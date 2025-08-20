"""连接管理器模块

提供数据库连接池管理和连接清理功能，解决mem0ai库中的连接泄漏问题。
"""

import os
import gc
import time
import threading
import psycopg2
from typing import Optional, Dict, Any
from contextlib import contextmanager
from mem0 import Memory
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ConnectionManager:
    """简化的mem0ai客户端连接管理器
    
    功能：
    - 自动创建和复用客户端连接
    - 定期清理空闲连接
    - 线程安全操作
    """
    
    def __init__(self, max_pool_size: int = 10, cleanup_interval: int = 300, idle_timeout: int = 600, max_lifetime: int = 3600):
        """初始化连接管理器
        
        Args:
            max_pool_size: 最大连接池大小
            cleanup_interval: 清理间隔（秒）
            idle_timeout: 空闲超时时间（秒）
            max_lifetime: 连接最大生存时间（秒）
        """
        self.max_pool_size = max_pool_size
        self.cleanup_interval = cleanup_interval
        self.idle_timeout = idle_timeout
        self.max_lifetime = max_lifetime
        
        self._clients: Dict[str, Memory] = {}
        self._connection_counts: Dict[str, int] = {}
        self._last_used: Dict[str, float] = {}
        self.client_created_time: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()
        
        logger.info(f"连接管理器已初始化，最大连接数: {max_pool_size}")
        
    def get_client(self, client_id: str = "default") -> Memory:
        """获取或创建mem0客户端
        
        Args:
            client_id: 客户端标识符
            
        Returns:
            Memory: mem0客户端实例
        """
        with self._lock:
            current_time = time.time()
            
            if client_id not in self._clients:
                # 检查连接池大小限制
                if len(self._clients) >= self.max_pool_size:
                    logger.warning(f"连接池已满 ({len(self._clients)}/{self.max_pool_size})，尝试清理空闲连接")
                    self._force_cleanup_idle_connections()
                
                logger.info(f"创建新的mem0客户端: {client_id}")
                
                self._clients[client_id] = self._create_client()
                self._connection_counts[client_id] = 0
                self.client_created_time[client_id] = current_time
                
            self._connection_counts[client_id] += 1
            self._last_used[client_id] = current_time
            
            logger.debug(f"获取客户端 {client_id}，使用次数: {self._connection_counts[client_id]}")
            
            return self._clients[client_id]
    
    def _create_client(self) -> Memory:
        """创建新的mem0客户端
        
        Returns:
            Memory: 新的mem0客户端实例
        """
        from utils import get_mem0_client
        return get_mem0_client()
    
    def release_client(self, client_id: str = "default") -> None:
        """释放客户端引用
        
        Args:
            client_id: 客户端标识符
        """
        with self._lock:
            if client_id in self._connection_counts:
                self._connection_counts[client_id] -= 1
                
                # 如果引用计数为0，清理客户端
                if self._connection_counts[client_id] <= 0:
                    self._cleanup_client(client_id)
    
    def _cleanup_client(self, client_id: str) -> None:
        """清理指定的客户端
        
        Args:
            client_id: 客户端标识符
        """
        if client_id in self._clients:
            logger.info(f"Cleaning up mem0 client: {client_id}")
            client = self._clients[client_id]
            
            try:
                # 尝试清理向量存储连接
                if hasattr(client, 'vector_store'):
                    vector_store = client.vector_store
                    if hasattr(vector_store, 'client'):
                        vector_client = vector_store.client
                        if hasattr(vector_client, 'close'):
                            logger.info("Closing vector store connection...")
                            vector_client.close()
                        elif hasattr(vector_client, '_client') and hasattr(vector_client._client, 'close'):
                            logger.info("Closing underlying vector store connection...")
                            vector_client._client.close()
                
                # 尝试清理数据库连接
                if hasattr(client, 'db'):
                    db = client.db
                    if hasattr(db, 'connection') and db.connection:
                        logger.info("Closing database connection...")
                        db.connection.close()
                    elif hasattr(db, 'engine') and db.engine:
                        logger.info("Disposing database engine...")
                        db.engine.dispose()
                
                # 删除客户端引用
                del self._clients[client_id]
                del self._connection_counts[client_id]
                
                logger.info(f"Client {client_id} cleanup completed")
                
            except Exception as e:
                logger.error(f"Error cleaning up client {client_id}: {e}")
    
    def cleanup_all(self) -> None:
        """清理所有客户端"""
        with self._lock:
            client_ids = list(self._clients.keys())
            for client_id in client_ids:
                self._cleanup_client(client_id)
        
        # 强制垃圾回收
        gc.collect()
        logger.info("All clients cleaned up")
    
    def get_connection_count(self) -> int:
        """获取当前数据库连接数
        
        Returns:
            int: 当前连接数
        """
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                return 0
                
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()
            
            # 查询当前连接数
            cursor.execute("""
                SELECT count(*) 
                FROM pg_stat_activity 
                WHERE state = 'active' OR state = 'idle'
            """)
            
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            return count
            
        except Exception as e:
            logger.error(f"Error getting connection count: {e}")
            return -1
    
    def start_periodic_cleanup(self, interval: int = None) -> None:
        """启动定期清理线程
        
        Args:
            interval: 清理间隔（秒），如果为None则使用配置中的值
        """
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            return
        
        # 使用默认或指定的清理间隔
        cleanup_interval = interval or self.cleanup_interval
            
        self._stop_cleanup.clear()
        self._cleanup_thread = threading.Thread(
            target=self._periodic_cleanup,
            args=(cleanup_interval,),
            daemon=True
        )
        self._cleanup_thread.start()
        logger.info(f"Started periodic cleanup thread (interval: {cleanup_interval}s)")
    
    def stop_periodic_cleanup(self) -> None:
        """停止定期清理线程"""
        self._stop_cleanup.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        logger.info("Stopped periodic cleanup thread")
    
    def _periodic_cleanup(self, interval: int) -> None:
        """定期清理工作线程
        
        Args:
            interval: 清理间隔（秒）
        """
        idle_timeout = self.idle_timeout
        max_lifetime = self.max_lifetime
        
        while not self._stop_cleanup.wait(interval):
            try:
                current_time = time.time()
                clients_to_remove = []
                
                with self._lock:
                    for client_id, last_used in self._last_used.items():
                        created_time = self.client_created_time.get(client_id, current_time)
                        
                        # 检查空闲超时
                        idle_time = current_time - last_used
                        # 检查最大生存时间
                        lifetime = current_time - created_time
                        
                        if idle_time > idle_timeout or lifetime > max_lifetime:
                            clients_to_remove.append(client_id)
                            reason = "idle timeout" if idle_time > idle_timeout else "max lifetime"
                            logger.debug(f"标记客户端 {client_id} 清理，原因: {reason}")
                
                for client_id in clients_to_remove:
                    self._cleanup_client(client_id)
                    logger.info(f"已清理客户端: {client_id}")
                    
                # 输出统计信息
                if interval >= 60:
                    self._log_stats()
                    
            except Exception as e:
                logger.error(f"定期清理过程中发生错误: {e}")
    
    def _force_cleanup_idle_connections(self) -> None:
        """强制清理空闲连接"""
        try:
            current_time = time.time()
            clients_to_remove = []
            idle_timeout = self.idle_timeout // 2  # 使用一半的空闲超时时间
            
            with self._lock:
                if not hasattr(self, '_last_used'):
                    self._last_used = {}
                    return
                    
                for client_id, last_used in self._last_used.items():
                    # 清理空闲时间超过阈值的客户端
                    if current_time - last_used > idle_timeout:
                        clients_to_remove.append(client_id)
            
            for client_id in clients_to_remove:
                self._cleanup_client(client_id)
                logger.info(f"强制清理空闲客户端: {client_id}")
                
        except Exception as e:
            logger.error(f"强制清理空闲连接时发生错误: {e}")
    
    def _log_stats(self) -> None:
        """输出连接统计信息"""
        try:
            with self._lock:
                active_clients = len(self._clients)
                total_connections = sum(self._connection_counts.values())
                
            db_connections = self.get_connection_count()
            
            logger.info(f"连接统计 - 活跃客户端: {active_clients}, 总连接数: {total_connections}, 数据库连接: {db_connections}")
            
            with self._lock:
                for client_id, count in self._connection_counts.items():
                    last_used = self._last_used.get(client_id, 0)
                    idle_time = time.time() - last_used
                    logger.debug(f"客户端 {client_id}: 使用次数={count}, 空闲时间={idle_time:.1f}s")
                        
        except Exception as e:
            logger.error(f"输出统计信息时发生错误: {e}")

# 全局连接管理器实例
_connection_manager: Optional[ConnectionManager] = None

def get_connection_manager() -> ConnectionManager:
    """获取全局连接管理器实例
    
    Returns:
        ConnectionManager: 连接管理器实例
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager

@contextmanager
def managed_mem0_client(client_id: str = "default"):
    """上下文管理器，自动管理mem0客户端的生命周期
    
    Args:
        client_id: 客户端标识符
        
    Yields:
        Memory: mem0客户端实例
    """
    manager = get_connection_manager()
    client = manager.get_client(client_id)
    try:
        yield client
    finally:
        manager.release_client(client_id)