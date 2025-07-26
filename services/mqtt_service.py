"""
MQTT服务组件
支持MQTT客户端连接聊天室，实现消息双向同步
"""
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Callable, Optional
import paho.mqtt.client as mqtt
from flask import current_app

from services.message_handler import get_message_handler
from services.user_manager import get_user_manager
from services.broadcast_manager import get_broadcast_manager

# 配置日志
logger = logging.getLogger(__name__)


class MQTTService:
    """MQTT服务管理器"""
    
    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883):
        """
        初始化MQTT服务
        
        Args:
            broker_host: MQTT代理服务器地址
            broker_port: MQTT代理服务器端口
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        
        # MQTT客户端配置
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # 服务组件
        self.message_handler = get_message_handler()
        self.user_manager = get_user_manager()
        self.broadcast_manager = get_broadcast_manager()
        
        # 状态管理
        self.is_connected = False
        self.is_running = False
        self.mqtt_users = {}  # client_id -> user_info 映射
        
        # MQTT主题配置
        self.topics = {
            'chat_in': 'chatroom/messages/in',      # 接收消息主题
            'chat_out': 'chatroom/messages/out',    # 发送消息主题
            'user_join': 'chatroom/users/join',     # 用户加入主题
            'user_leave': 'chatroom/users/leave',   # 用户离开主题
            'system': 'chatroom/system'             # 系统消息主题
        }
        
        # 统计信息
        self.stats = {
            'mqtt_users_count': 0,
            'messages_received': 0,
            'messages_sent': 0,
            'connect_time': None,
            'last_message_time': None
        }
        
        logger.info(f"MQTT服务初始化完成: {broker_host}:{broker_port}")
    
    def start(self) -> bool:
        """
        启动MQTT服务
        
        Returns:
            启动是否成功
        """
        try:
            if self.is_running:
                logger.warning("MQTT服务已在运行")
                return True
            
            # 连接到MQTT代理
            logger.info(f"连接到MQTT代理: {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            
            # 启动网络循环
            self.client.loop_start()
            self.is_running = True
            
            # 等待连接建立
            retry_count = 0
            while not self.is_connected and retry_count < 10:
                time.sleep(0.5)
                retry_count += 1
            
            if self.is_connected:
                logger.info("MQTT服务启动成功")
                return True
            else:
                logger.error("MQTT连接超时")
                self.stop()
                return False
                
        except Exception as e:
            logger.error(f"MQTT服务启动失败: {e}")
            return False
    
    def stop(self):
        """停止MQTT服务"""
        try:
            if not self.is_running:
                return
            
            self.is_running = False
            
            # 发送断开消息
            if self.is_connected:
                self._publish_system_message("MQTT服务即将停止")
                time.sleep(0.1)
            
            # 断开连接
            self.client.loop_stop()
            self.client.disconnect()
            
            # 清理MQTT用户
            for client_id in list(self.mqtt_users.keys()):
                self._handle_mqtt_user_leave(client_id)
            
            self.is_connected = False
            logger.info("MQTT服务已停止")
            
        except Exception as e:
            logger.error(f"MQTT服务停止异常: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT连接回调"""
        if rc == 0:
            self.is_connected = True
            self.stats['connect_time'] = datetime.now()
            logger.info("MQTT连接成功")
            
            # 订阅相关主题
            for topic_name, topic in self.topics.items():
                if topic_name in ['chat_in', 'user_join', 'user_leave']:
                    client.subscribe(topic)
                    logger.info(f"订阅主题: {topic}")
            
            # 发送连接成功消息
            self._publish_system_message("MQTT服务已连接")
            
        else:
            logger.error(f"MQTT连接失败，错误代码: {rc}")
            self.is_connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT断开连接回调"""
        self.is_connected = False
        logger.info(f"MQTT连接断开，代码: {rc}")
    
    def _on_message(self, client, userdata, message):
        """MQTT消息回调"""
        try:
            topic = message.topic
            payload = message.payload.decode('utf-8')
            
            logger.info(f"收到MQTT消息: {topic} -> {payload}")
            self.stats['messages_received'] += 1
            self.stats['last_message_time'] = datetime.now()
            
            # 解析消息内容
            try:
                msg_data = json.loads(payload)
            except json.JSONDecodeError:
                # 如果不是JSON格式，当作普通文本处理
                msg_data = {'message': payload}
            
            # 根据主题处理消息
            if topic == self.topics['chat_in']:
                self._handle_chat_message(msg_data)
            elif topic == self.topics['user_join']:
                self._handle_mqtt_user_join(msg_data)
            elif topic == self.topics['user_leave']:
                self._handle_mqtt_user_leave_msg(msg_data)
            
        except Exception as e:
            logger.error(f"处理MQTT消息异常: {e}")
    
    def _handle_chat_message(self, msg_data: Dict[str, Any]):
        """
        处理聊天消息
        
        Args:
            msg_data: 消息数据
        """
        try:
            # 提取消息信息
            username = msg_data.get('username', 'MQTT用户')
            message = msg_data.get('message', '')
            client_id = msg_data.get('client_id', 'unknown')
            
            if not message.strip():
                return
            
            # 确保MQTT用户存在
            self._ensure_mqtt_user_exists(client_id, username)
            
            # 处理消息
            result = self.message_handler.process_message(
                message_content=message,
                username=f"{username} (MQTT)",
                session_id=f"mqtt_{client_id}"
            )
            
            if result['success'] and result['message']:
                # 广播消息到所有WebSocket客户端
                self.broadcast_manager.broadcast_message(
                    message=result['message'],
                    ai_response=result['ai_response'],
                    room="main"
                )
                
                # 转发到MQTT out主题
                self._publish_chat_message(result['message'], result['ai_response'])
                
                logger.info(f"MQTT消息处理成功: {username} -> {message[:50]}...")
            else:
                logger.warning(f"MQTT消息处理失败: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"处理MQTT聊天消息异常: {e}")
    
    def _handle_mqtt_user_join(self, msg_data: Dict[str, Any]):
        """
        处理MQTT用户加入
        
        Args:
            msg_data: 用户信息
        """
        try:
            client_id = msg_data.get('client_id', 'unknown')
            username = msg_data.get('username', f'MQTT用户{client_id}')
            
            # 创建MQTT用户
            user_info = {
                'client_id': client_id,
                'username': username,
                'join_time': datetime.now(),
                'message_count': 0
            }
            
            self.mqtt_users[client_id] = user_info
            self.stats['mqtt_users_count'] = len(self.mqtt_users)
            
            # 发送系统消息
            self._publish_system_message(f"MQTT用户 {username} 加入了聊天室")
            
            logger.info(f"MQTT用户加入: {username} (client_id: {client_id})")
            
        except Exception as e:
            logger.error(f"处理MQTT用户加入异常: {e}")
    
    def _handle_mqtt_user_leave(self, client_id: str):
        """
        处理MQTT用户离开
        
        Args:
            client_id: MQTT客户端ID
        """
        try:
            if client_id in self.mqtt_users:
                user_info = self.mqtt_users.pop(client_id)
                self.stats['mqtt_users_count'] = len(self.mqtt_users)
                
                # 发送系统消息
                self._publish_system_message(f"MQTT用户 {user_info['username']} 离开了聊天室")
                
                logger.info(f"MQTT用户离开: {user_info['username']} (client_id: {client_id})")
                
        except Exception as e:
            logger.error(f"处理MQTT用户离开异常: {e}")
    
    def _handle_mqtt_user_leave_msg(self, msg_data: Dict[str, Any]):
        """处理MQTT用户离开消息"""
        client_id = msg_data.get('client_id', 'unknown')
        self._handle_mqtt_user_leave(client_id)
    
    def _ensure_mqtt_user_exists(self, client_id: str, username: str):
        """确保MQTT用户存在"""
        if client_id not in self.mqtt_users:
            self._handle_mqtt_user_join({
                'client_id': client_id,
                'username': username
            })
    
    def _publish_chat_message(self, message, ai_response=None):
        """
        发布聊天消息到MQTT
        
        Args:
            message: 用户消息对象
            ai_response: AI回复对象（可选）
        """
        try:
            if not self.is_connected:
                return
            
            # 发布用户消息
            msg_data = {
                'type': 'user_message',
                'username': message.username,
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
                'message_id': message.id
            }
            
            self.client.publish(self.topics['chat_out'], json.dumps(msg_data))
            self.stats['messages_sent'] += 1
            
            # 发布AI回复
            if ai_response:
                ai_data = {
                    'type': 'ai_response',
                    'username': ai_response.username,
                    'content': ai_response.content,
                    'timestamp': ai_response.timestamp.isoformat(),
                    'message_id': ai_response.id
                }
                
                self.client.publish(self.topics['chat_out'], json.dumps(ai_data))
                self.stats['messages_sent'] += 1
                
        except Exception as e:
            logger.error(f"发布MQTT消息异常: {e}")
    
    def _publish_system_message(self, message: str):
        """
        发布系统消息到MQTT
        
        Args:
            message: 系统消息内容
        """
        try:
            if not self.is_connected:
                return
            
            sys_data = {
                'type': 'system_message',
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
            
            self.client.publish(self.topics['system'], json.dumps(sys_data))
            self.stats['messages_sent'] += 1
            
        except Exception as e:
            logger.error(f"发布系统消息异常: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取MQTT服务统计信息"""
        return {
            'is_connected': self.is_connected,
            'is_running': self.is_running,
            'broker_info': f"{self.broker_host}:{self.broker_port}",
            'mqtt_users_count': self.stats['mqtt_users_count'],
            'messages_received': self.stats['messages_received'],
            'messages_sent': self.stats['messages_sent'],
            'connect_time': self.stats['connect_time'].isoformat() if self.stats['connect_time'] else None,
            'last_message_time': self.stats['last_message_time'].isoformat() if self.stats['last_message_time'] else None,
            'active_topics': list(self.topics.values()),
            'mqtt_users': list(self.mqtt_users.values())
        }
    
    def send_message_to_mqtt(self, message, ai_response=None):
        """
        从聊天室向MQTT发送消息
        
        Args:
            message: 消息对象
            ai_response: AI回复对象（可选）
        """
        self._publish_chat_message(message, ai_response)


# 全局MQTT服务实例
_mqtt_service = None
_mqtt_service_lock = threading.Lock()


def get_mqtt_service(broker_host: str = "localhost", broker_port: int = 1883) -> MQTTService:
    """
    获取全局MQTT服务实例
    
    Args:
        broker_host: MQTT代理服务器地址
        broker_port: MQTT代理服务器端口
        
    Returns:
        MQTT服务实例
    """
    global _mqtt_service
    
    with _mqtt_service_lock:
        if _mqtt_service is None:
            _mqtt_service = MQTTService(broker_host, broker_port)
        return _mqtt_service


def start_mqtt_service(broker_host: str = "localhost", broker_port: int = 1883) -> bool:
    """
    启动MQTT服务
    
    Args:
        broker_host: MQTT代理服务器地址
        broker_port: MQTT代理服务器端口
        
    Returns:
        启动是否成功
    """
    mqtt_service = get_mqtt_service(broker_host, broker_port)
    return mqtt_service.start()


def stop_mqtt_service():
    """停止MQTT服务"""
    global _mqtt_service
    
    with _mqtt_service_lock:
        if _mqtt_service:
            _mqtt_service.stop()
            _mqtt_service = None


class MQTTMessageBridge:
    """MQTT消息桥接器 - 双向同步聊天室和MQTT消息"""
    
    def __init__(self, mqtt_service: MQTTService):
        self.mqtt_service = mqtt_service
        self.message_handler = get_message_handler()
        
    def forward_to_mqtt(self, message, ai_response=None):
        """将聊天室消息转发到MQTT"""
        self.mqtt_service.send_message_to_mqtt(message, ai_response)
        
    def process_from_mqtt(self, mqtt_message: Dict[str, Any]):
        """处理从MQTT收到的消息"""
        return self.mqtt_service._handle_chat_message(mqtt_message)