#!/usr/bin/env python3
"""
简单的WebSocket客户端测试脚本
用于测试AI聊天室的WebSocket功能
"""
import socketio
import time
import threading

# 创建Socket.IO客户端
sio = socketio.Client()

# 测试数据
test_username = "TestUser"
test_messages = [
    "Hello, this is a test message!",
    "Testing WebSocket functionality",
    "@AI How are you today?",
    "Another test message"
]

@sio.event
def connect():
    print("✅ Connected to WebSocket server")
    
    # 发送加入聊天室请求
    print(f"🚀 Joining chat room as {test_username}")
    sio.emit('join_room', {'username': test_username})

@sio.event
def connect_success(data):
    print(f"✅ Connection success: {data}")

@sio.event
def join_room_success(data):
    print(f"✅ Joined chat room successfully: {data['message']}")
    print(f"📝 Chat history: {len(data['chat_history'])} messages")
    print(f"👥 Online users: {len(data['online_users'])} users")
    
    # 开始发送测试消息
    threading.Thread(target=send_test_messages, daemon=True).start()

@sio.event
def join_room_error(data):
    print(f"❌ Failed to join room: {data['error']}")

@sio.event
def message_sent(data):
    print(f"✅ Message sent successfully: {data['message']}")

@sio.event
def message_error(data):
    print(f"❌ Message send failed: {data['error']}")

@sio.event
def broadcast_message(data):
    print(f"📨 Received broadcast: {data.get('type', 'unknown')} - {data}")

@sio.event
def disconnect():
    print("❌ Disconnected from WebSocket server")

@sio.event
def connect_error(data):
    print(f"❌ Connection error: {data}")

def send_test_messages():
    """发送测试消息"""
    time.sleep(2)  # 等待连接稳定
    
    for i, message in enumerate(test_messages):
        print(f"📤 Sending message {i+1}: {message}")
        sio.emit('send_message', {'message': message})
        time.sleep(3)  # 等待响应
    
    # 测试完成，等待一下然后断开
    time.sleep(5)
    print("🔄 Test completed, disconnecting...")
    sio.disconnect()

def main():
    """主函数"""
    print("🚀 Starting WebSocket test...")
    
    try:
        # 连接到服务器
        sio.connect('http://localhost:5000', transports=['websocket'])
        
        # 等待测试完成
        sio.wait()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    print("✨ Test finished!")

if __name__ == '__main__':
    main()