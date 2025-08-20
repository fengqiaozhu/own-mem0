#!/usr/bin/env python3
"""
数据库连接泄漏测试脚本

此脚本用于测试 mem0ai 客户端的连接管理，检查是否存在连接泄漏问题。
通过创建和销毁多个 Memory 实例来模拟实际使用场景。
"""

import os
import sys
import time
import psutil
import psycopg2
from contextlib import contextmanager
from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils import get_mem0_client

load_dotenv()

def get_db_connection_info():
    """
    获取数据库连接信息
    
    Returns:
        dict: 包含连接参数的字典
    """
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL 环境变量未设置")
    
    # 解析 DATABASE_URL
    from urllib.parse import urlparse
    parsed = urlparse(database_url)
    
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path[1:] if parsed.path else 'postgres',
        'user': parsed.username,
        'password': parsed.password
    }

def count_database_connections():
    """
    统计当前数据库连接数
    
    Returns:
        int: 当前连接数，如果无法连接则返回 -1
    """
    try:
        conn_info = get_db_connection_info()
        
        # 创建临时连接来查询连接数
        with psycopg2.connect(**conn_info) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE state = 'active' OR state = 'idle'
                """)
                return cursor.fetchone()[0]
    except Exception as e:
        print(f"无法查询数据库连接数: {e}")
        return -1

@contextmanager
def memory_client_context():
    """
    上下文管理器，用于安全地创建和清理 Memory 客户端
    
    Yields:
        Memory: mem0ai Memory 客户端实例
    """
    client = None
    try:
        print("创建 Memory 客户端...")
        client = get_mem0_client()
        yield client
    except Exception as e:
        print(f"Memory 客户端操作失败: {e}")
        raise
    finally:
        if client:
            print("清理 Memory 客户端...")
            try:
                # 显式清理连接
                if hasattr(client, 'vector_store') and hasattr(client.vector_store, 'client'):
                    vector_client = client.vector_store.client
                    if hasattr(vector_client, 'close'):
                        print("关闭向量存储连接...")
                        vector_client.close()
                    elif hasattr(vector_client, '_client') and hasattr(vector_client._client, 'close'):
                        print("关闭底层向量存储连接...")
                        vector_client._client.close()
                
                # 尝试关闭数据库连接
                if hasattr(client, 'db') and hasattr(client.db, 'connection'):
                    print("关闭数据库连接...")
                    client.db.connection.close()
                
                # 删除客户端引用
                del client
                print("Memory 客户端清理完成")
            except Exception as cleanup_error:
                print(f"清理过程中出错: {cleanup_error}")
            
            # 强制垃圾回收
            import gc
            gc.collect()
            print("垃圾回收完成")

def test_memory_operations(client, test_id):
    """
    测试基本的内存操作
    
    Args:
        client: Memory 客户端实例
        test_id: 测试标识符
    """
    try:
        # 添加内存
        result = client.add(
            f"测试内存 {test_id}: 用户喜欢编程和机器学习",
            user_id=f"test_user_{test_id}"
        )
        print(f"测试 {test_id}: 添加内存成功")
        
        # 搜索内存
        memories = client.search(
            query="编程",
            user_id=f"test_user_{test_id}",
            limit=5
        )
        print(f"测试 {test_id}: 搜索到 {len(memories.get('results', []))} 条内存")
        
        return True
    except Exception as e:
        print(f"测试 {test_id}: 内存操作失败 - {e}")
        return False

def run_connection_leak_test(num_iterations=10, delay_between_tests=2):
    """
    运行连接泄漏测试
    
    Args:
        num_iterations: 测试迭代次数
        delay_between_tests: 测试间隔时间（秒）
    """
    print(f"开始连接泄漏测试 - {num_iterations} 次迭代")
    print("=" * 60)
    
    # 记录初始状态
    initial_connections = count_database_connections()
    print(f"初始数据库连接数: {initial_connections}")
    
    successful_tests = 0
    failed_tests = 0
    
    for i in range(1, num_iterations + 1):
        print(f"\n--- 测试迭代 {i}/{num_iterations} ---")
        
        # 记录测试前连接数
        pre_test_connections = count_database_connections()
        print(f"测试前连接数: {pre_test_connections}")
        
        try:
            # 使用上下文管理器创建和清理客户端
            with memory_client_context() as client:
                success = test_memory_operations(client, i)
                if success:
                    successful_tests += 1
                else:
                    failed_tests += 1
        except Exception as e:
            print(f"测试 {i} 失败: {e}")
            failed_tests += 1
        
        # 等待一段时间让连接完全关闭
        time.sleep(delay_between_tests)
        
        # 记录测试后连接数
        post_test_connections = count_database_connections()
        print(f"测试后连接数: {post_test_connections}")
        
        # 检查连接泄漏
        if post_test_connections > pre_test_connections:
            print(f"⚠️  检测到可能的连接泄漏: +{post_test_connections - pre_test_connections} 连接")
        elif post_test_connections == pre_test_connections:
            print("✅ 连接数保持稳定")
        else:
            print(f"✅ 连接数减少: -{pre_test_connections - post_test_connections} 连接")
    
    # 最终统计
    final_connections = count_database_connections()
    print("\n" + "=" * 60)
    print("测试完成 - 最终统计:")
    print(f"成功测试: {successful_tests}")
    print(f"失败测试: {failed_tests}")
    print(f"初始连接数: {initial_connections}")
    print(f"最终连接数: {final_connections}")
    
    if final_connections > initial_connections:
        leaked_connections = final_connections - initial_connections
        print(f"🔴 检测到连接泄漏: {leaked_connections} 个连接未关闭")
        print("建议检查连接清理逻辑")
    else:
        print("🟢 未检测到连接泄漏")
    
    return {
        'successful_tests': successful_tests,
        'failed_tests': failed_tests,
        'initial_connections': initial_connections,
        'final_connections': final_connections,
        'leaked_connections': max(0, final_connections - initial_connections)
    }

def main():
    """
    主函数
    """
    print("数据库连接泄漏测试脚本")
    print("此脚本将测试 mem0ai 客户端的连接管理")
    
    try:
        # 检查环境变量
        if not os.getenv('DATABASE_URL'):
            print("错误: DATABASE_URL 环境变量未设置")
            return 1
        
        # 运行测试
        result = run_connection_leak_test(num_iterations=5, delay_between_tests=3)
        
        # 根据结果返回退出码
        if result['leaked_connections'] > 0:
            print(f"\n退出码: 1 (检测到 {result['leaked_connections']} 个连接泄漏)")
            return 1
        elif result['failed_tests'] > 0:
            print(f"\n退出码: 2 ({result['failed_tests']} 个测试失败)")
            return 2
        else:
            print("\n退出码: 0 (所有测试通过，无连接泄漏)")
            return 0
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 130
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        import traceback
        print(f"详细错误信息: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)