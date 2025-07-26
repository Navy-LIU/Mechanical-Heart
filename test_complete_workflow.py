#!/usr/bin/env python3
"""
完整的IP用户名重复使用功能测试工作流
"""
import socketio
import time
import sqlite3
from datetime import datetime
from threading import Event

def setup_test_data():
    """为127.0.0.1设置测试数据"""
    print("=== 设置测试数据 ===")
    
    try:
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()
        
        test_ip = "127.0.0.1"  # 本地测试IP
        test_usernames = ["小明", "小红", "小刚"]
        
        # 先清除可能存在的测试数据
        cursor.execute('DELETE FROM ip_username_history WHERE ip_address = ?', (test_ip,))
        
        # 插入测试的IP-用户名关联数据
        for i, username in enumerate(test_usernames):
            now = datetime.now()
            cursor.execute('''
                INSERT INTO ip_username_history 
                (ip_address, username, first_used, last_used, usage_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (test_ip, username, now.isoformat(), now.isoformat(), i + 1))
        
        conn.commit()
        conn.close()
        
        print(f"已为IP {test_ip} 设置测试用户名: {test_usernames}")
        return True
        
    except Exception as e:
        print(f"设置测试数据失败: {e}")
        return False

def test_complete_workflow():
    """测试完整的工作流程"""
    print("\n=== 测试完整工作流程 ===")
    
    # 创建Socket.IO客户端
    sio = socketio.Client()
    
    # 用于同步的事件
    suggestion_received = Event()
    join_received = Event()
    suggestion_data = None
    join_data = None

    @sio.on('connect')
    def on_connect():
        print("✅ 已连接到服务器")

    @sio.on('username_suggestions')
    def on_username_suggestions(data):
        nonlocal suggestion_data
        suggestion_data = data
        print(f"✅ 收到用户名建议")
        suggestion_received.set()

    @sio.on('username_suggestions_error')
    def on_username_suggestions_error(data):
        nonlocal suggestion_data
        suggestion_data = data
        print(f"❌ 用户名建议错误: {data}")
        suggestion_received.set()

    @sio.on('join_room_success')
    def on_join_room_success(data):
        nonlocal join_data
        join_data = data
        print(f"✅ 收到加入房间成功")
        join_received.set()
    
    @sio.on('join_room_error')
    def on_join_room_error(data):
        nonlocal join_data
        join_data = data
        print(f"❌ 加入房间失败: {data}")
        join_received.set()

    try:
        # 连接到服务器
        print("1. 连接到服务器...")
        sio.connect('http://localhost:5000')
        time.sleep(1)
        
        # 请求用户名建议
        print("2. 请求历史用户名建议...")
        sio.emit('get_username_suggestions')
        
        # 等待响应
        if suggestion_received.wait(timeout=10):
            if suggestion_data and suggestion_data.get('success'):
                suggestions = suggestion_data.get('data', {}).get('suggestions', {})
                print(f"   - 有历史记录: {suggestions.get('has_history')}")
                print(f"   - 建议用户名: {suggestions.get('suggested_username')}")
                print(f"   - 历史用户名: {suggestions.get('recent_usernames')}")
                print(f"   - 可用用户名: {suggestions.get('available_usernames')}")
                
                if suggestions.get('has_history') and suggestions.get('available_usernames'):
                    suggested_username = suggestions['available_usernames'][0]
                    print(f"\n3. 使用建议的用户名 '{suggested_username}' 加入聊天室...")
                    
                    # 使用建议的用户名加入聊天室
                    sio.emit('join_room', {'username': suggested_username})
                    
                    # 等待加入结果
                    if join_received.wait(timeout=10):
                        if join_data:
                            if 'error' in join_data:
                                # 这是join_room_error事件
                                print(f"❌ 加入聊天室失败: {join_data.get('error')}")
                            elif 'user' in join_data:
                                # 这是join_room_success事件
                                print("✅ 成功使用历史用户名加入聊天室")
                                print(f"   - 用户信息: {join_data.get('user', {}).get('username')}")
                                return True
                            else:
                                print(f"❌ 未知的加入结果格式: {join_data}")
                        else:
                            print("❌ 加入结果为空")
                    else:
                        print("❌ 加入聊天室响应超时")
                else:
                    print("ℹ️ 没有可用的历史用户名")
                    return True  # 这也是正常情况
            else:
                error = suggestion_data.get('error') if suggestion_data else '未知错误'
                print(f"❌ 获取用户名建议失败: {error}")
        else:
            print("❌ 获取用户名建议响应超时")
        
        return False
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
        return False
    finally:
        # 断开连接
        if sio.connected:
            print("4. 断开连接...")
            sio.disconnect()

def cleanup_test_data():
    """清理测试数据"""
    print("\n=== 清理测试数据 ===")
    
    try:
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()
        
        test_ip = "127.0.0.1"
        cursor.execute('DELETE FROM ip_username_history WHERE ip_address = ?', (test_ip,))
        
        conn.commit()
        conn.close()
        
        print("测试数据已清理")
        return True
        
    except Exception as e:
        print(f"清理测试数据失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始完整工作流程测试...\n")
    
    # 执行测试步骤
    tests = [
        ("设置测试数据", setup_test_data),
        ("完整工作流程", test_complete_workflow),
        ("清理测试数据", cleanup_test_data),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"执行: {test_name}")
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
        print("🎉 完整工作流程测试通过！")
        print("💡 功能说明: 用户IP重复访问时会提供历史用户名建议")
    else:
        print("⚠️ 部分测试失败，请检查实现")

if __name__ == "__main__":
    main()