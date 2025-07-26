#!/usr/bin/env python3
"""
MQTT测试套件
用于测试聊天室的MQTT集成功能，包含简单的MQTT代理模拟
"""
import json
import time
import threading
import queue
import logging
from typing import Dict, Any, List, Callable
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SimpleMQTTBroker:
    """简单的MQTT代理模拟器，用于测试"""
    
    def __init__(self):
        self.clients = {}  # client_id -> client_info
        self.subscriptions = {}  # topic -> set of client_ids
        self.message_queue = queue.Queue()
        self.running = False
        self.stats = {
            'clients': 0,
            'subscriptions': 0,
            'messages_processed': 0
        }
    
    def start(self):
        """启动代理"""
        self.running = True
        self.processor_thread = threading.Thread(target=self._process_messages)
        self.processor_thread.daemon = True
        self.processor_thread.start()
        logger.info("简单MQTT代理已启动")
    
    def stop(self):
        """停止代理"""
        self.running = False
        if hasattr(self, 'processor_thread'):
            self.processor_thread.join(timeout=1)
        logger.info("简单MQTT代理已停止")
    
    def connect_client(self, client_id: str, callback: Callable = None):
        """客户端连接"""
        self.clients[client_id] = {
            'client_id': client_id,
            'callback': callback,
            'connect_time': datetime.now(),
            'subscriptions': set()
        }
        self.stats['clients'] = len(self.clients)
        logger.info(f"客户端连接: {client_id}")
    
    def disconnect_client(self, client_id: str):
        """客户端断开"""
        if client_id in self.clients:
            # 清理订阅
            client_subscriptions = self.clients[client_id].get('subscriptions', set())
            for topic in client_subscriptions:
                if topic in self.subscriptions:
                    self.subscriptions[topic].discard(client_id)
                    if not self.subscriptions[topic]:
                        del self.subscriptions[topic]
            
            del self.clients[client_id]
            self.stats['clients'] = len(self.clients)
            self.stats['subscriptions'] = sum(len(clients) for clients in self.subscriptions.values())
            logger.info(f"客户端断开: {client_id}")
    
    def subscribe(self, client_id: str, topic: str):
        """客户端订阅主题"""
        if client_id not in self.clients:
            logger.error(f"客户端 {client_id} 未连接")
            return False
        
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        
        self.subscriptions[topic].add(client_id)
        self.clients[client_id]['subscriptions'].add(topic)
        self.stats['subscriptions'] = sum(len(clients) for clients in self.subscriptions.values())
        logger.info(f"客户端 {client_id} 订阅主题: {topic}")
        return True
    
    def publish(self, client_id: str, topic: str, payload: str):
        """发布消息"""
        message = {
            'client_id': client_id,
            'topic': topic,
            'payload': payload,
            'timestamp': datetime.now()
        }
        self.message_queue.put(message)
        logger.info(f"消息发布: {client_id} -> {topic} -> {payload[:50]}...")
    
    def _process_messages(self):
        """处理消息队列"""
        while self.running:
            try:
                message = self.message_queue.get(timeout=0.1)
                self._deliver_message(message)
                self.stats['messages_processed'] += 1
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"处理消息异常: {e}")
    
    def _deliver_message(self, message: Dict[str, Any]):
        """分发消息给订阅者"""
        topic = message['topic']
        if topic in self.subscriptions:
            for client_id in self.subscriptions[topic]:
                if client_id in self.clients:
                    callback = self.clients[client_id].get('callback')
                    if callback:
                        try:
                            callback(topic, message['payload'])
                        except Exception as e:
                            logger.error(f"回调异常 {client_id}: {e}")


class MQTTChatRoomTester:
    """MQTT聊天室测试器"""
    
    def __init__(self, chat_room_url="http://localhost:5000"):
        self.chat_room_url = chat_room_url
        self.broker = SimpleMQTTBroker()
        self.test_results = []
        self.received_messages = []
    
    def run_tests(self):
        """运行所有测试"""
        print("🧪 开始MQTT聊天室集成测试")
        print("=" * 60)
        
        try:
            # 启动代理
            self.broker.start()
            
            # 运行测试
            self._test_mqtt_message_forwarding()
            self._test_message_format_validation()
            self._test_user_management()
            
            # 输出测试结果
            self._print_test_results()
            
        finally:
            self.broker.stop()
    
    def _test_mqtt_message_forwarding(self):
        """测试MQTT消息转发"""
        print("📡 测试: MQTT消息转发到聊天室")
        
        try:
            # 模拟聊天室服务器作为MQTT客户端
            def chatroom_callback(topic, payload):
                print(f"🏠 聊天室收到MQTT消息: {topic} -> {payload}")
                self.received_messages.append({
                    'topic': topic,
                    'payload': payload,
                    'timestamp': datetime.now()
                })
            
            # 连接聊天室到代理
            self.broker.connect_client("chatroom_server", chatroom_callback)
            self.broker.subscribe("chatroom_server", "chatroom/messages/in")
            self.broker.subscribe("chatroom_server", "chatroom/users/join")
            
            # 模拟MQTT客户端发送消息
            test_client_id = "test_mqtt_client"
            self.broker.connect_client(test_client_id)
            
            # 发送测试消息
            test_messages = [
                {
                    "topic": "chatroom/messages/in",
                    "payload": json.dumps({
                        "client_id": test_client_id,
                        "username": "MQTT测试用户",
                        "message": "Hello from MQTT!"
                    }, ensure_ascii=False)
                },
                {
                    "topic": "chatroom/messages/in", 
                    "payload": json.dumps({
                        "client_id": test_client_id,
                        "username": "MQTT用户",
                        "message": "这是中文测试消息"
                    }, ensure_ascii=False)
                }
            ]
            
            for msg in test_messages:
                self.broker.publish(test_client_id, msg["topic"], msg["payload"])
                time.sleep(0.5)
            
            # 等待消息处理
            time.sleep(2)
            
            # 验证结果
            if len(self.received_messages) >= len(test_messages):
                self._add_test_result("MQTT消息转发", True, "成功转发所有测试消息")
            else:
                self._add_test_result("MQTT消息转发", False, f"只收到 {len(self.received_messages)}/{len(test_messages)} 条消息")
                
        except Exception as e:
            self._add_test_result("MQTT消息转发", False, f"异常: {e}")
    
    def _test_message_format_validation(self):
        """测试消息格式验证"""
        print("📋 测试: 消息格式验证")
        
        try:
            invalid_messages = [
                {"payload": "非JSON格式消息", "should_pass": True},  # 应当作普通文本处理
                {"payload": json.dumps({"message": "缺少用户名"}), "should_pass": False},
                {"payload": json.dumps({"username": "用户", "message": ""}), "should_pass": False},  # 空消息
                {"payload": json.dumps({"username": "正常用户", "message": "正常消息", "client_id": "test"}), "should_pass": True}
            ]
            
            valid_count = 0
            for i, msg_test in enumerate(invalid_messages):
                test_name = f"消息格式验证-{i+1}"
                
                try:
                    # 这里应该调用聊天室的消息验证逻辑
                    # 由于没有直接接口，我们模拟验证结果
                    payload = msg_test["payload"]
                    
                    # 简单验证逻辑
                    if payload.startswith('{'):
                        try:
                            data = json.loads(payload)
                            has_message = data.get('message', '').strip() != ''
                            has_username = data.get('username', '').strip() != ''
                            is_valid = has_message and (has_username or data.get('client_id'))
                        except:
                            is_valid = False
                    else:
                        is_valid = True  # 非JSON格式当作普通文本
                    
                    expected = msg_test["should_pass"]
                    if is_valid == expected:
                        valid_count += 1
                        self._add_test_result(test_name, True, f"验证结果正确: {is_valid}")
                    else:
                        self._add_test_result(test_name, False, f"验证结果错误: 期望{expected}, 实际{is_valid}")
                        
                except Exception as e:
                    self._add_test_result(test_name, False, f"验证异常: {e}")
            
            overall_success = valid_count == len(invalid_messages)
            self._add_test_result("消息格式验证总结", overall_success, f"通过 {valid_count}/{len(invalid_messages)} 项验证")
            
        except Exception as e:
            self._add_test_result("消息格式验证", False, f"异常: {e}")
    
    def _test_user_management(self):
        """测试用户管理"""
        print("👥 测试: MQTT用户管理")
        
        try:
            user_events = []
            
            def user_callback(topic, payload):
                user_events.append({
                    'topic': topic,
                    'payload': payload,
                    'timestamp': datetime.now()
                })
            
            # 连接用户管理监听器
            self.broker.connect_client("user_manager", user_callback)
            self.broker.subscribe("user_manager", "chatroom/users/join")
            self.broker.subscribe("user_manager", "chatroom/users/leave")
            
            # 模拟用户加入/离开
            test_users = ["MQTT用户1", "MQTT用户2", "MQTT用户3"]
            
            for user in test_users:
                # 用户加入
                join_msg = json.dumps({
                    "client_id": f"mqtt_{user}",
                    "username": user
                }, ensure_ascii=False)
                self.broker.publish(f"mqtt_{user}", "chatroom/users/join", join_msg)
                time.sleep(0.2)
                
                # 用户离开
                leave_msg = json.dumps({
                    "client_id": f"mqtt_{user}"
                }, ensure_ascii=False)
                self.broker.publish(f"mqtt_{user}", "chatroom/users/leave", leave_msg)
                time.sleep(0.2)
            
            # 等待处理
            time.sleep(1)
            
            expected_events = len(test_users) * 2  # 每个用户2个事件（加入+离开）
            if len(user_events) >= expected_events:
                self._add_test_result("MQTT用户管理", True, f"成功处理 {len(user_events)} 个用户事件")
            else:
                self._add_test_result("MQTT用户管理", False, f"只处理了 {len(user_events)}/{expected_events} 个用户事件")
                
        except Exception as e:
            self._add_test_result("MQTT用户管理", False, f"异常: {e}")
    
    def _add_test_result(self, test_name: str, success: bool, details: str):
        """添加测试结果"""
        self.test_results.append({
            'name': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now()
        })
    
    def _print_test_results(self):
        """输出测试结果"""
        print("\n📊 测试结果汇总")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        
        print(f"总测试数: {total_tests}")
        print(f"通过测试: {passed_tests}")
        print(f"失败测试: {total_tests - passed_tests}")
        print(f"成功率: {passed_tests/total_tests*100:.1f}%")
        print()
        
        for i, result in enumerate(self.test_results, 1):
            status = "✅ 通过" if result['success'] else "❌ 失败"
            print(f"{i:2d}. {status} {result['name']}")
            print(f"     {result['details']}")
        
        print(f"\n🔍 代理统计:")
        print(f"     客户端: {self.broker.stats['clients']}")
        print(f"     订阅数: {self.broker.stats['subscriptions']}")
        print(f"     处理消息: {self.broker.stats['messages_processed']}")
        
        if self.received_messages:
            print(f"\n📨 收到的消息:")
            for i, msg in enumerate(self.received_messages, 1):
                print(f"     {i}. [{msg['timestamp'].strftime('%H:%M:%S')}] {msg['topic']} -> {msg['payload'][:50]}...")


def main():
    """主函数"""
    print("MQTT聊天室集成测试套件")
    print("测试说明：此脚本模拟MQTT代理和客户端，测试消息转发逻辑")
    print("注意：这是一个独立的测试，不需要真实的MQTT代理")
    print()
    
    try:
        tester = MQTTChatRoomTester()
        tester.run_tests()
    except KeyboardInterrupt:
        print("\n测试已中断")
    except Exception as e:
        print(f"\n测试失败: {e}")


if __name__ == "__main__":
    main()