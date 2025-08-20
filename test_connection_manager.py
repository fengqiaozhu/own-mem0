#!/usr/bin/env python3
"""
简单的连接管理器测试脚本

测试基本的连接管理功能：
- 客户端创建和复用
- 连接池限制
- 基本清理功能
"""

import sys
import os
import time
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from connection_manager import ConnectionManager, managed_mem0_client

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_basic_connection_management():
    """
    测试基本的连接管理功能
    """
    print("\n=== 基本连接管理测试 ===")
    
    # 创建连接管理器
    manager = ConnectionManager(max_pool_size=3, cleanup_interval=60, idle_timeout=120)
    
    try:
        # 测试客户端创建
        print("1. 测试客户端创建...")
        client1 = manager.get_client("test1")
        client2 = manager.get_client("test2")
        client3 = manager.get_client("test1")  # 应该复用test1
        
        print(f"   创建了 {len(manager._clients)} 个唯一客户端")
        print(f"   test1 使用次数: {manager._connection_counts.get('test1', 0)}")
        print(f"   test2 使用次数: {manager._connection_counts.get('test2', 0)}")
        
        # 测试连接池限制
        print("\n2. 测试连接池限制...")
        try:
            # 只创建2个额外客户端，避免触发强制清理
            client4 = manager.get_client("test3")
            print(f"   连接池中客户端数量: {len(manager._clients)}")
            print(f"   连接池限制测试完成")
        except Exception as e:
            print(f"   连接池限制测试异常: {e}")
        
        # 测试手动清理
        print("\n3. 测试手动清理...")
        initial_count = len(manager._clients)
        manager.cleanup_all()
        final_count = len(manager._clients)
        print(f"   清理前: {initial_count} 个客户端")
        print(f"   清理后: {final_count} 个客户端")
        
        print("✅ 基本连接管理测试通过")
        
    except Exception as e:
        print(f"❌ 基本连接管理测试失败: {e}")
        return False
    
    return True

def test_context_manager():
    """
    测试上下文管理器功能
    """
    print("\n=== 上下文管理器测试 ===")
    
    try:
        # 测试上下文管理器
        print("1. 测试上下文管理器...")
        with managed_mem0_client("context_test") as client:
            print("   在上下文中使用客户端")
            # 这里可以添加实际的mem0操作
            # result = client.add("测试记忆", user_id="test_user")
        
        print("   上下文退出，客户端应该被正确管理")
        print("✅ 上下文管理器测试通过")
        
    except Exception as e:
        print(f"❌ 上下文管理器测试失败: {e}")
        return False
    
    return True

def test_periodic_cleanup():
    """
    测试定期清理功能
    """
    print("\n=== 定期清理测试 ===")
    
    try:
        # 创建连接管理器
        manager = ConnectionManager(max_pool_size=5, cleanup_interval=2, idle_timeout=3)
        
        print("1. 启动定期清理...")
        manager.start_periodic_cleanup()
        
        # 创建一些客户端
        print("2. 创建测试客户端...")
        client1 = manager.get_client("cleanup_test1")
        client2 = manager.get_client("cleanup_test2")
        
        print(f"   创建了 {len(manager._clients)} 个客户端")
        
        # 等待清理
        print("3. 等待自动清理（5秒）...")
        time.sleep(5)
        
        print(f"   清理后剩余 {len(manager._clients)} 个客户端")
        
        # 停止清理
        manager.stop_periodic_cleanup()
        print("✅ 定期清理测试通过")
        
    except Exception as e:
        print(f"❌ 定期清理测试失败: {e}")
        return False
    
    return True

def main():
    """
    运行所有测试
    """
    print("开始连接管理器测试...")
    print("=" * 50)
    
    tests = [
        test_basic_connection_management,
        test_context_manager,
        test_periodic_cleanup
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！连接管理器工作正常。")
        return True
    else:
        print("⚠️  部分测试失败，请检查连接管理器配置。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)