#!/usr/bin/env python3
"""
数据库连接重置脚本

此脚本用于清理数据库中的僵尸连接和空闲连接，解决"too many clients already"错误。
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv

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
    parsed = urlparse(database_url)
    
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path[1:] if parsed.path else 'postgres',
        'user': parsed.username,
        'password': parsed.password
    }

def show_current_connections():
    """
    显示当前数据库连接状态
    """
    try:
        conn_info = get_db_connection_info()
        
        with psycopg2.connect(**conn_info) as conn:
            with conn.cursor() as cursor:
                # 查询当前连接数
                cursor.execute("""
                    SELECT 
                        count(*) as total_connections,
                        count(*) FILTER (WHERE state = 'active') as active_connections,
                        count(*) FILTER (WHERE state = 'idle') as idle_connections,
                        count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
                    FROM pg_stat_activity
                """)
                
                result = cursor.fetchone()
                print(f"总连接数: {result[0]}")
                print(f"活跃连接: {result[1]}")
                print(f"空闲连接: {result[2]}")
                print(f"事务中空闲连接: {result[3]}")
                
                # 查询最大连接数
                cursor.execute("SHOW max_connections")
                max_conn = cursor.fetchone()[0]
                print(f"最大连接数: {max_conn}")
                
                # 显示详细连接信息
                print("\n详细连接信息:")
                cursor.execute("""
                    SELECT 
                        pid,
                        usename,
                        application_name,
                        client_addr,
                        state,
                        query_start,
                        state_change,
                        EXTRACT(EPOCH FROM (now() - query_start)) as query_duration_seconds
                    FROM pg_stat_activity 
                    WHERE pid != pg_backend_pid()
                    ORDER BY query_start DESC
                    LIMIT 20
                """)
                
                connections = cursor.fetchall()
                if connections:
                    print(f"{'PID':<8} {'用户':<12} {'应用':<15} {'客户端IP':<15} {'状态':<20} {'查询时长(秒)':<12}")
                    print("-" * 90)
                    for conn in connections:
                        pid, user, app, client, state, query_start, state_change, duration = conn
                        duration_str = f"{duration:.1f}" if duration else "N/A"
                        print(f"{pid:<8} {user:<12} {app or 'N/A':<15} {client or 'local':<15} {state:<20} {duration_str:<12}")
                else:
                    print("没有找到其他连接")
                    
    except Exception as e:
        print(f"无法查询数据库连接状态: {e}")
        return False
    
    return True

def terminate_idle_connections(max_idle_time_minutes=30):
    """
    终止长时间空闲的连接
    
    Args:
        max_idle_time_minutes: 最大空闲时间（分钟）
    
    Returns:
        int: 被终止的连接数
    """
    try:
        conn_info = get_db_connection_info()
        
        with psycopg2.connect(**conn_info) as conn:
            with conn.cursor() as cursor:
                # 查找长时间空闲的连接
                cursor.execute("""
                    SELECT pid, usename, application_name, state, 
                           EXTRACT(EPOCH FROM (now() - state_change))/60 as idle_minutes
                    FROM pg_stat_activity 
                    WHERE pid != pg_backend_pid()
                      AND state IN ('idle', 'idle in transaction')
                      AND EXTRACT(EPOCH FROM (now() - state_change))/60 > %s
                    ORDER BY state_change
                """, (max_idle_time_minutes,))
                
                idle_connections = cursor.fetchall()
                
                if not idle_connections:
                    print(f"没有找到超过 {max_idle_time_minutes} 分钟的空闲连接")
                    return 0
                
                print(f"找到 {len(idle_connections)} 个长时间空闲的连接:")
                for conn in idle_connections:
                    pid, user, app, state, idle_minutes = conn
                    print(f"  PID {pid}: {user} ({app or 'N/A'}) - {state} - 空闲 {idle_minutes:.1f} 分钟")
                
                # 询问用户是否要终止这些连接
                response = input(f"\n是否要终止这 {len(idle_connections)} 个空闲连接? (y/N): ")
                if response.lower() != 'y':
                    print("操作已取消")
                    return 0
                
                # 终止空闲连接
                terminated_count = 0
                for conn in idle_connections:
                    pid = conn[0]
                    try:
                        cursor.execute("SELECT pg_terminate_backend(%s)", (pid,))
                        result = cursor.fetchone()[0]
                        if result:
                            terminated_count += 1
                            print(f"  已终止 PID {pid}")
                        else:
                            print(f"  无法终止 PID {pid}")
                    except Exception as e:
                        print(f"  终止 PID {pid} 时出错: {e}")
                
                print(f"\n成功终止 {terminated_count} 个连接")
                return terminated_count
                
    except Exception as e:
        print(f"终止空闲连接时出错: {e}")
        return 0

def force_terminate_connections(exclude_current=True):
    """
    强制终止所有非当前的连接（谨慎使用）
    
    Args:
        exclude_current: 是否排除当前连接
    
    Returns:
        int: 被终止的连接数
    """
    try:
        conn_info = get_db_connection_info()
        
        with psycopg2.connect(**conn_info) as conn:
            with conn.cursor() as cursor:
                # 查找所有其他连接
                if exclude_current:
                    cursor.execute("""
                        SELECT pid, usename, application_name, state
                        FROM pg_stat_activity 
                        WHERE pid != pg_backend_pid()
                    """)
                else:
                    cursor.execute("""
                        SELECT pid, usename, application_name, state
                        FROM pg_stat_activity
                    """)
                
                all_connections = cursor.fetchall()
                
                if not all_connections:
                    print("没有找到其他连接")
                    return 0
                
                print(f"找到 {len(all_connections)} 个连接:")
                for conn in all_connections:
                    pid, user, app, state = conn
                    print(f"  PID {pid}: {user} ({app or 'N/A'}) - {state}")
                
                # 警告用户
                print("\n⚠️  警告: 这将强制终止所有其他数据库连接!")
                response = input(f"确定要继续吗? 请输入 'FORCE' 来确认: ")
                if response != 'FORCE':
                    print("操作已取消")
                    return 0
                
                # 强制终止所有连接
                terminated_count = 0
                for conn in all_connections:
                    pid = conn[0]
                    try:
                        cursor.execute("SELECT pg_terminate_backend(%s)", (pid,))
                        result = cursor.fetchone()[0]
                        if result:
                            terminated_count += 1
                            print(f"  已终止 PID {pid}")
                        else:
                            print(f"  无法终止 PID {pid}")
                    except Exception as e:
                        print(f"  终止 PID {pid} 时出错: {e}")
                
                print(f"\n成功终止 {terminated_count} 个连接")
                return terminated_count
                
    except Exception as e:
        print(f"强制终止连接时出错: {e}")
        return 0

def main():
    """
    主函数
    """
    print("数据库连接重置脚本")
    print("=" * 40)
    
    try:
        # 检查环境变量
        if not os.getenv('DATABASE_URL'):
            print("错误: DATABASE_URL 环境变量未设置")
            return 1
        
        while True:
            print("\n请选择操作:")
            print("1. 查看当前连接状态")
            print("2. 终止长时间空闲的连接")
            print("3. 强制终止所有连接 (危险操作)")
            print("4. 退出")
            
            choice = input("\n请输入选择 (1-4): ").strip()
            
            if choice == '1':
                print("\n--- 当前连接状态 ---")
                show_current_connections()
                
            elif choice == '2':
                print("\n--- 终止空闲连接 ---")
                idle_time = input("请输入最大空闲时间（分钟，默认30）: ").strip()
                try:
                    idle_time = int(idle_time) if idle_time else 30
                except ValueError:
                    idle_time = 30
                terminate_idle_connections(idle_time)
                
            elif choice == '3':
                print("\n--- 强制终止所有连接 ---")
                force_terminate_connections()
                
            elif choice == '4':
                print("退出程序")
                break
                
            else:
                print("无效选择，请重试")
                
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        return 130
    except Exception as e:
        print(f"\n程序执行过程中发生错误: {e}")
        import traceback
        print(f"详细错误信息: {traceback.format_exc()}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)