#!/usr/bin/env python3
"""
MQTT测试客户端
用于测试聊天室的MQTT集成功能
"""
import json
import time
import threading
import paho.mqtt.client as mqtt
from datetime import datetime


class MQTTTestClient:
    """MQTT测试客户端"""
    
    def __init__(self, client_id="test_client", broker_host="localhost", broker_port=1883):
        self.client_id = client_id
        self.broker_host = broker_host
        self.broker_port = broker_port
        
        # 创建MQTT客户端
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # 主题配置
        self.topics = {
            'chat_in': 'chatroom/messages/in',
            'chat_out': 'chatroom/messages/out',
            'user_join': 'chatroom/users/join',
            'user_leave': 'chatroom/users/leave',
            'system': 'chatroom/system'
        }
        
        self.is_connected = False
        self.received_messages = []
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self.is_connected = True
            print(f"✓ MQTT连接成功: {self.broker_host}:{self.broker_port}")
            
            # 订阅输出主题
            for topic in [self.topics['chat_out'], self.topics['system']]:
                client.subscribe(topic)
                print(f"✓ 订阅主题: {topic}")
        else:
            print(f"✗ MQTT连接失败，错误代码: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        self.is_connected = False
        print(f"✗ MQTT连接断开，代码: {rc}")
    
    def _on_message(self, client, userdata, message):
        """消息回调"""
        try:
            topic = message.topic
            payload = message.payload.decode('utf-8')
            timestamp = datetime.now().isoformat()
            
            print(f"📨 收到消息 [{timestamp}]")
            print(f"   主题: {topic}")
            print(f"   内容: {payload}")
            
            # 尝试解析JSON
            try:
                msg_data = json.loads(payload)
                print(f"   JSON解析: {json.dumps(msg_data, indent=2, ensure_ascii=False)}")
            except json.JSONDecodeError:
                print(f"   非JSON格式消息")
            
            print("-" * 60)
            
            # 记录消息
            self.received_messages.append({
                'topic': topic,
                'payload': payload,
                'timestamp': timestamp
            })
            
        except Exception as e:
            print(f"✗ 处理消息异常: {e}")
    
    def connect(self):
        """连接到MQTT代理"""
        try:
            print(f"🔌 正在连接到MQTT代理: {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # 等待连接建立
            retry_count = 0
            while not self.is_connected and retry_count < 20:
                time.sleep(0.5)
                retry_count += 1
            
            if self.is_connected:
                return True
            else:
                print(f"✗ MQTT连接超时")
                return False
        except Exception as e:
            print(f"✗ MQTT连接异常: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        try:
            if self.is_connected:
                # 发送离开消息
                self.send_user_leave()
                time.sleep(0.1)
            
            self.client.loop_stop()
            self.client.disconnect()
            print("🔌 MQTT连接已断开")
        except Exception as e:
            print(f"✗ 断开连接异常: {e}")
    
    def send_user_join(self, username="MQTT测试用户"):
        """发送用户加入消息"""
        try:
            if not self.is_connected:
                print("✗ MQTT未连接，无法发送消息")
                return False
            
            join_data = {
                'client_id': self.client_id,
                'username': username
            }
            
            self.client.publish(
                self.topics['user_join'], 
                json.dumps(join_data, ensure_ascii=False)
            )
            print(f"📤 发送用户加入消息: {username}")
            return True
        except Exception as e:
            print(f"✗ 发送用户加入消息失败: {e}")
            return False
    
    def send_user_leave(self):
        """发送用户离开消息"""
        try:
            if not self.is_connected:
                return False
            
            leave_data = {
                'client_id': self.client_id
            }
            
            self.client.publish(
                self.topics['user_leave'], 
                json.dumps(leave_data, ensure_ascii=False)
            )
            print(f"📤 发送用户离开消息")
            return True
        except Exception as e:
            print(f"✗ 发送用户离开消息失败: {e}")
            return False
    
    def send_chat_message(self, username="MQTT测试用户", message="Hello from MQTT!"):
        """发送聊天消息"""
        try:
            if not self.is_connected:
                print("✗ MQTT未连接，无法发送消息")
                return False
            
            chat_data = {
                'client_id': self.client_id,
                'username': username,
                'message': message
            }
            
            self.client.publish(
                self.topics['chat_in'], 
                json.dumps(chat_data, ensure_ascii=False)
            )
            print(f"📤 发送聊天消息: {username} -> {message}")
            return True
        except Exception as e:
            print(f"✗ 发送聊天消息失败: {e}")
            return False
    
    def get_received_messages(self):
        """获取接收到的消息列表"""
        return self.received_messages.copy()


def test_mqtt_integration():
    """测试MQTT集成功能"""
    print("🧪 开始MQTT集成测试")
    print("=" * 60)
    
    # 创建测试客户端
    test_client = MQTTTestClient("test_client_001")
    
    try:
        # 连接
        if not test_client.connect():
            print("✗ 测试失败：无法连接到MQTT代理")
            return False
        
        # 发送用户加入消息
        test_client.send_user_join("MQTT测试用户")
        time.sleep(1)
        
        # 发送聊天消息
        test_messages = [
            "Hello from MQTT client!",
            "这是一条中文测试消息",
            "MQTT消息转发测试",
            "最后一条测试消息"
        ]
        
        for msg in test_messages:
            test_client.send_chat_message("MQTT测试用户", msg)
            time.sleep(2)  # 等待处理
        
        # 等待接收回复
        print("⏳ 等待接收消息...")
        time.sleep(5)
        
        # 检查接收到的消息
        received = test_client.get_received_messages()
        print(f"📊 测试结果:")
        print(f"   发送消息: {len(test_messages)} 条")
        print(f"   接收消息: {len(received)} 条")
        
        if received:
            print(f"✓ MQTT消息转发测试成功")
            for i, msg in enumerate(received, 1):
                print(f"   {i}. [{msg['timestamp']}] {msg['topic']} -> {msg['payload'][:100]}...")
        else:
            print(f"⚠️  没有接收到任何消息")
        
        # 发送用户离开消息
        test_client.send_user_leave()
        time.sleep(1)
        
        return True
        
    except Exception as e:
        print(f"✗ 测试异常: {e}")
        return False
    finally:
        test_client.disconnect()


if __name__ == "__main__":
    print("MQTT聊天室集成测试工具")
    print("使用说明：")
    print("1. 确保MQTT代理服务器正在运行 (默认localhost:1883)")
    print("2. 确保聊天室服务器已启动且启用了MQTT功能")
    print("3. 运行此脚本进行集成测试")
    print()
    
    # 询问是否开始测试
    try:
        input("按回车键开始测试，或Ctrl+C取消...")
        test_mqtt_integration()
    except KeyboardInterrupt:
        print("\n测试已取消")
    except Exception as e:
        print(f"\n测试失败: {e}")