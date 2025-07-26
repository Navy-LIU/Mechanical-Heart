#!/usr/bin/env python3
"""
测试WebSocket客户端 - 模拟前端加入聊天室的过程
"""
import socketio
import time
import asyncio

# 创建Socket.IO客户端
sio = socketio.Client()

@sio.event
def connect():
    print('✅ 连接成功！')
    print('🚀 发送加入聊天室请求...')
    sio.emit('join_room', {'username': '测试用户123'})

@sio.event  
def disconnect():
    print('❌ 连接断开')

@sio.on('join_room_success')
def on_join_success(data):
    print(f'🎉 加入聊天室成功！')
    print(f'   用户: {data.get("user", {}).get("username", "未知")}')
    print(f'   会话ID: {data.get("session_id", "未知")}')
    print(f'   在线用户数: {len(data.get("online_users", []))}')
    print(f'   聊天历史数量: {len(data.get("chat_history", []))}')
    
    # 测试发送消息
    print('💬 发送测试消息...')
    sio.emit('send_message', {'message': '你好，这是一条测试消息！'})

@sio.on('join_room_error')
def on_join_error(data):
    print(f'❌ 加入聊天室失败: {data.get("error", "未知错误")}')

@sio.on('message_sent')
def on_message_sent(data):
    print(f'📨 消息发送成功!')
    print(f'   消息内容: {data.get("message_data", {}).get("content", "未知")}')
    
    # 测试AI对话
    print('🤖 测试AI对话...')
    sio.emit('send_message', {'message': '@AI 你好，请介绍一下你自己'})

@sio.on('message_error')
def on_message_error(data):
    print(f'❌ 消息发送失败: {data.get("error", "未知错误")}')

@sio.on('error')
def on_error(data):
    print(f'💥 Socket错误: {data}')

def test_websocket():
    try:
        print('🔌 正在连接到WebSocket服务器...')
        sio.connect('http://localhost:5000')
        
        # 等待事件处理
        print('⏳ 等待事件处理...')
        time.sleep(10)  # 等待10秒处理各种事件
        
    except Exception as e:
        print(f'💥 连接失败: {e}')
    finally:
        try:
            sio.disconnect()
            print('👋 测试完成，断开连接')
        except:
            pass

if __name__ == '__main__':
    test_websocket()