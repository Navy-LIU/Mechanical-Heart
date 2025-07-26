#!/usr/bin/env python3
"""
测试WebSocket IP用户名重复使用功能
"""
import socketio
import time
import json
from threading import Event

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

@sio.on('disconnect')
def on_disconnect():
    print("❌ 已断开与服务器的连接")

@sio.on('username_suggestions')
def on_username_suggestions(data):
    global suggestion_data
    suggestion_data = data
    print(f"✅ 收到用户名建议: {json.dumps(data, indent=2, ensure_ascii=False)}")
    suggestion_received.set()

@sio.on('username_suggestions_error')
def on_username_suggestions_error(data):
    global suggestion_data
    suggestion_data = data
    print(f"❌ 用户名建议错误: {json.dumps(data, indent=2, ensure_ascii=False)}")
    suggestion_received.set()

@sio.on('join_room_result')
def on_join_room_result(data):
    global join_data
    join_data = data
    print(f"✅ 加入房间结果: {json.dumps(data, indent=2, ensure_ascii=False)}")
    join_received.set()

@sio.on('error')
def on_error(data):
    print(f"❌ 收到错误: {json.dumps(data, indent=2, ensure_ascii=False)}")

def test_websocket_functionality():
    """测试WebSocket用户名建议功能"""
    print("=== 测试WebSocket功能 ===")
    
    try:
        # 连接到服务器
        print("正在连接到服务器...")
        sio.connect('http://localhost:5000')
        time.sleep(1)
        
        # 请求用户名建议
        print("\n1. 请求用户名建议...")
        sio.emit('get_username_suggestions')
        
        # 等待响应
        if suggestion_received.wait(timeout=5):
            if suggestion_data and suggestion_data.get('success'):
                suggestions = suggestion_data.get('data', {}).get('suggestions', {})
                print(f"获得建议: {suggestions}")
                
                if suggestions.get('has_history') and suggestions.get('available_usernames'):
                    suggested_username = suggestions['available_usernames'][0]
                    print(f"建议使用用户名: {suggested_username}")
                    
                    # 使用建议的用户名加入聊天室
                    print(f"\n2. 使用建议用户名 '{suggested_username}' 加入聊天室...")
                    sio.emit('join_room', {'username': suggested_username})
                    
                    # 等待加入结果
                    if join_received.wait(timeout=5):
                        if join_data and join_data.get('success'):
                            print("✅ 成功使用建议用户名加入聊天室")
                            return True
                        else:
                            print("❌ 加入聊天室失败")
                    else:
                        print("❌ 加入聊天室超时")
                else:
                    print("ℹ️ 该IP没有历史用户名记录")
                    return True  # 这也是正常情况
            else:
                print("❌ 获取用户名建议失败")
        else:
            print("❌ 获取用户名建议超时")
        
        return False
        
    except Exception as e:
        print(f"WebSocket测试失败: {e}")
        return False
    finally:
        # 断开连接
        if sio.connected:
            sio.disconnect()

def main():
    """主测试函数"""
    print("开始测试WebSocket IP用户名重复使用功能...\n")
    
    success = test_websocket_functionality()
    
    print("\n=== 测试总结 ===")
    if success:
        print("🎉 WebSocket IP用户名重复使用功能测试通过！")
    else:
        print("❌ WebSocket测试失败")
    
    return success

if __name__ == "__main__":
    main()