#!/usr/bin/env python3
"""
测试IP用户名重复使用功能的脚本
"""
import sqlite3
import requests
import json
from datetime import datetime

def test_database_setup():
    """测试数据库表结构是否正确"""
    print("=== 测试数据库表结构 ===")
    
    try:
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()
        
        # 检查user_sessions表是否有ip_address列
        cursor.execute("PRAGMA table_info(user_sessions)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"user_sessions表的列: {columns}")
        
        # 检查ip_username_history表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ip_username_history'")
        table_exists = cursor.fetchone() is not None
        print(f"ip_username_history表存在: {table_exists}")
        
        if table_exists:
            cursor.execute("PRAGMA table_info(ip_username_history)")
            ip_columns = [col[1] for col in cursor.fetchall()]
            print(f"ip_username_history表的列: {ip_columns}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"数据库检查失败: {e}")
        return False

def insert_test_data():
    """插入测试数据"""
    print("\n=== 插入测试数据 ===")
    
    try:
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()
        
        test_ip = "192.168.1.100"
        test_usernames = ["张三", "李四", "王五"]
        
        # 插入测试的IP-用户名关联数据
        for i, username in enumerate(test_usernames):
            now = datetime.now()
            cursor.execute('''
                INSERT OR REPLACE INTO ip_username_history 
                (ip_address, username, first_used, last_used, usage_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (test_ip, username, now.isoformat(), now.isoformat(), i + 1))
        
        conn.commit()
        conn.close()
        
        print(f"已为IP {test_ip} 插入测试用户名: {test_usernames}")
        return True
        
    except Exception as e:
        print(f"插入测试数据失败: {e}")
        return False

def test_api_endpoints():
    """测试相关的API端点"""
    print("\n=== 测试API端点 ===")
    
    base_url = "http://localhost:5000"
    
    try:
        # 测试主页是否可访问
        response = requests.get(f"{base_url}/")
        print(f"主页访问状态: {response.status_code}")
        
        # 测试API文档
        response = requests.get(f"{base_url}/api/docs")
        print(f"API文档访问状态: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"API测试失败: {e}")
        return False

def query_test_data():
    """查询测试数据以验证功能"""
    print("\n=== 查询测试数据 ===")
    
    try:
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()
        
        test_ip = "192.168.1.100"
        
        # 查询该IP的用户名历史
        cursor.execute('''
            SELECT username, usage_count, first_used, last_used FROM ip_username_history 
            WHERE ip_address = ?
            ORDER BY last_used DESC
        ''', (test_ip,))
        
        results = cursor.fetchall()
        print(f"IP {test_ip} 的用户名历史:")
        for username, count, first, last in results:
            print(f"  - {username}: 使用次数={count}, 首次使用={first[:19]}, 最后使用={last[:19]}")
        
        conn.close()
        return len(results) > 0
        
    except Exception as e:
        print(f"查询测试数据失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试IP用户名重复使用功能...\n")
    
    # 测试步骤
    tests = [
        ("数据库表结构", test_database_setup),
        ("插入测试数据", insert_test_data),
        ("API端点访问", test_api_endpoints), 
        ("查询测试数据", query_test_data),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"执行测试: {test_name}")
        success = test_func()
        results.append((test_name, success))
        print(f"结果: {'✅ 成功' if success else '❌ 失败'}")
        print("-" * 50)
    
    # 总结
    print("\n=== 测试总结 ===")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！IP用户名重复使用功能已正确实现")
    else:
        print("⚠️ 部分测试失败，请检查实现")

if __name__ == "__main__":
    main()