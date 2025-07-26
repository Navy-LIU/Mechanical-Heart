"""
消息广播机制
实现WebSocket消息广播、用户状态变更通知和AI响应消息处理
"""
import logging
from typing import Dict, List, Any, Optional, Set, Callable
from datetime import datetime
from enum import Enum
import json
import threading
from collections import defaultdict, deque

from models.message import Message
from models.user import User

# 配置日志
logger = logging.getLogger(__name__)


class BroadcastType(Enum):
    """广播类型枚举"""
    NEW_MESSAGE = "new_message"
    AI_RESPONSE = "ai_response"
    MESSAGE_WITH_AI_RESPONSE = "message_with_ai_response"
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"
    USER_LIST_UPDATE = "user_list_update"
    SYSTEM_NOTIFICATION = "system_notification"
    TYPING_INDICATOR = "typing_indicator"
    ERROR_NOTIFICATION = "error_notification"


class BroadcastManager:
    """广播管理器"""
    
    def __init__(self):
        """初始化广播管理器"""
        self._subscribers = defaultdict(set)  # 事件类型 -> 订阅者集合
        self._socket_subscribers = {}  # socket_id -> 订阅者信息
        self._room_subscribers = defaultdict(set)  # 房间 -> socket_id集合
        self._user_sockets = {}  # username -> socket_id
        self._socket_users = {}  # socket_id -> username
        
        # 广播统计
        self.stats = {
            'total_broadcasts': 0,
            'successful_broadcasts': 0,
            'failed_broadcasts': 0,
            'subscribers_count': 0,
            'last_broadcast_time': None,
            'broadcast_types': defaultdict(int)
        }
        
        # 线程安全锁
        self._lock = threading.RLock()
        
        # 广播历史（用于调试）
        self._broadcast_history = deque(maxlen=100)
    
    def subscribe(self, socket_id: str, username: str = None, room: str = "main", 
                 event_types: List[BroadcastType] = None) -> bool:
        """
        订阅广播事件
        
        Args:
            socket_id: Socket连接ID
            username: 用户名（可选）
            room: 房间名称，默认为"main"
            event_types: 订阅的事件类型列表，None表示订阅所有事件
            
        Returns:
            是否订阅成功
        """
        try:
            with self._lock:
                # 默认订阅所有事件类型
                if event_types is None:
                    event_types = list(BroadcastType)
                
                # 记录订阅者信息
                subscriber_info = {
                    'socket_id': socket_id,
                    'username': username,
                    'room': room,
                    'event_types': event_types,
                    'subscribe_time': datetime.now(),
                    'last_activity': datetime.now()
                }
                
                self._socket_subscribers[socket_id] = subscriber_info
                
                # 添加到事件订阅
                for event_type in event_types:
                    self._subscribers[event_type].add(socket_id)
                
                # 添加到房间订阅
                self._room_subscribers[room].add(socket_id)
                
                # 记录用户-Socket映射
                if username:
                    self._user_sockets[username] = socket_id
                    self._socket_users[socket_id] = username
                
                self.stats['subscribers_count'] = len(self._socket_subscribers)
                
                logger.info(f"订阅成功: socket={socket_id}, user={username}, room={room}")
                return True
                
        except Exception as e:
            logger.error(f"订阅失败: {e}")
            return False
    
    def unsubscribe(self, socket_id: str) -> bool:
        """
        取消订阅
        
        Args:
            socket_id: Socket连接ID
            
        Returns:
            是否取消成功
        """
        try:
            with self._lock:
                if socket_id not in self._socket_subscribers:
                    return False
                
                subscriber_info = self._socket_subscribers[socket_id]
                
                # 从事件订阅中移除
                for event_type in subscriber_info['event_types']:
                    self._subscribers[event_type].discard(socket_id)
                
                # 从房间订阅中移除
                room = subscriber_info['room']
                self._room_subscribers[room].discard(socket_id)
                
                # 清理用户-Socket映射
                username = subscriber_info.get('username')
                if username:
                    self._user_sockets.pop(username, None)
                    self._socket_users.pop(socket_id, None)
                
                # 移除订阅者信息
                del self._socket_subscribers[socket_id]
                
                self.stats['subscribers_count'] = len(self._socket_subscribers)
                
                logger.info(f"取消订阅成功: socket={socket_id}, user={username}")
                return True
                
        except Exception as e:
            logger.error(f"取消订阅失败: {e}")
            return False
    
    def broadcast_message(self, message: Message, ai_response: Message = None, 
                         room: str = "main", exclude_sockets: Set[str] = None) -> Dict[str, Any]:
        """
        广播新消息
        
        Args:
            message: 消息对象
            ai_response: AI回复消息（可选）
            room: 目标房间
            exclude_sockets: 排除的Socket ID集合
            
        Returns:
            广播结果
        """
        broadcast_type = BroadcastType.MESSAGE_WITH_AI_RESPONSE if ai_response else BroadcastType.NEW_MESSAGE
        
        broadcast_data = {
            'type': broadcast_type.value,
            'message': message.format_for_display(),
            'timestamp': datetime.now().isoformat(),
            'room': room
        }
        
        if ai_response:
            broadcast_data['ai_response'] = ai_response.format_for_display()
        
        return self._broadcast(broadcast_type, broadcast_data, room, exclude_sockets)
    
    def broadcast_user_join(self, username: str, user_info: Dict[str, Any], 
                           room: str = "main") -> Dict[str, Any]:
        """
        广播用户加入通知
        
        Args:
            username: 用户名
            user_info: 用户信息
            room: 房间名称
            
        Returns:
            广播结果
        """
        broadcast_data = {
            'type': BroadcastType.USER_JOIN.value,
            'username': username,
            'user_info': user_info,
            'message': f"{username} 加入了聊天室",
            'timestamp': datetime.now().isoformat(),
            'room': room
        }
        
        return self._broadcast(BroadcastType.USER_JOIN, broadcast_data, room)
    
    def broadcast_user_leave(self, username: str, user_info: Dict[str, Any], 
                            room: str = "main") -> Dict[str, Any]:
        """
        广播用户离开通知
        
        Args:
            username: 用户名
            user_info: 用户信息
            room: 房间名称
            
        Returns:
            广播结果
        """
        broadcast_data = {
            'type': BroadcastType.USER_LEAVE.value,
            'username': username,
            'user_info': user_info,
            'message': f"{username} 离开了聊天室",
            'timestamp': datetime.now().isoformat(),
            'room': room
        }
        
        return self._broadcast(BroadcastType.USER_LEAVE, broadcast_data, room)
    
    def broadcast_user_list_update(self, users: List[Dict[str, Any]], user_count: int, 
                                  room: str = "main") -> Dict[str, Any]:
        """
        广播用户列表更新
        
        Args:
            users: 用户列表
            user_count: 用户数量
            room: 房间名称
            
        Returns:
            广播结果
        """
        broadcast_data = {
            'type': BroadcastType.USER_LIST_UPDATE.value,
            'users': users,
            'user_count': user_count,
            'timestamp': datetime.now().isoformat(),
            'room': room
        }
        
        return self._broadcast(BroadcastType.USER_LIST_UPDATE, broadcast_data, room)
    
    def broadcast_system_notification(self, message: str, level: str = "info", 
                                    room: str = "main") -> Dict[str, Any]:
        """
        广播系统通知
        
        Args:
            message: 通知消息
            level: 通知级别（info, warning, error）
            room: 房间名称
            
        Returns:
            广播结果
        """
        broadcast_data = {
            'type': BroadcastType.SYSTEM_NOTIFICATION.value,
            'message': message,
            'level': level,
            'timestamp': datetime.now().isoformat(),
            'room': room
        }
        
        return self._broadcast(BroadcastType.SYSTEM_NOTIFICATION, broadcast_data, room)
    
    def broadcast_typing_indicator(self, username: str, is_typing: bool, 
                                  room: str = "main") -> Dict[str, Any]:
        """
        广播打字指示器
        
        Args:
            username: 用户名
            is_typing: 是否正在打字
            room: 房间名称
            
        Returns:
            广播结果
        """
        broadcast_data = {
            'type': BroadcastType.TYPING_INDICATOR.value,
            'username': username,
            'is_typing': is_typing,
            'timestamp': datetime.now().isoformat(),
            'room': room
        }
        
        # 排除发送者自己
        exclude_sockets = set()
        if username in self._user_sockets:
            exclude_sockets.add(self._user_sockets[username])
        
        return self._broadcast(BroadcastType.TYPING_INDICATOR, broadcast_data, room, exclude_sockets)
    
    def broadcast_error_notification(self, error_message: str, error_code: str = None, 
                                   target_socket: str = None, room: str = "main") -> Dict[str, Any]:
        """
        广播错误通知
        
        Args:
            error_message: 错误消息
            error_code: 错误代码（可选）
            target_socket: 目标Socket ID（如果指定，只发送给特定用户）
            room: 房间名称
            
        Returns:
            广播结果
        """
        broadcast_data = {
            'type': BroadcastType.ERROR_NOTIFICATION.value,
            'error_message': error_message,
            'error_code': error_code,
            'timestamp': datetime.now().isoformat(),
            'room': room
        }
        
        if target_socket:
            # 发送给特定用户
            return self._send_to_socket(target_socket, broadcast_data)
        else:
            return self._broadcast(BroadcastType.ERROR_NOTIFICATION, broadcast_data, room)
    
    def _broadcast(self, event_type: BroadcastType, data: Dict[str, Any], 
                  room: str = "main", exclude_sockets: Set[str] = None) -> Dict[str, Any]:
        """
        内部广播方法
        
        Args:
            event_type: 事件类型
            data: 广播数据
            room: 房间名称
            exclude_sockets: 排除的Socket ID集合
            
        Returns:
            广播结果
        """
        try:
            with self._lock:
                self.stats['total_broadcasts'] += 1
                self.stats['broadcast_types'][event_type.value] += 1
                self.stats['last_broadcast_time'] = datetime.now()
                
                # 获取目标Socket列表
                target_sockets = self._get_target_sockets(event_type, room, exclude_sockets)
                
                if not target_sockets:
                    logger.warning(f"没有找到目标订阅者: event_type={event_type.value}, room={room}")
                    return {
                        'success': True,
                        'target_count': 0,
                        'successful_count': 0,
                        'failed_count': 0,
                        'event_type': event_type.value
                    }
                
                # 执行广播
                successful_count = 0
                failed_count = 0
                
                for socket_id in target_sockets:
                    if self._send_to_socket(socket_id, data)['success']:
                        successful_count += 1
                    else:
                        failed_count += 1
                
                # 更新统计
                if successful_count > 0:
                    self.stats['successful_broadcasts'] += 1
                if failed_count > 0:
                    self.stats['failed_broadcasts'] += 1
                
                # 记录广播历史
                self._broadcast_history.append({
                    'event_type': event_type.value,
                    'data': data,
                    'target_count': len(target_sockets),
                    'successful_count': successful_count,
                    'failed_count': failed_count,
                    'timestamp': datetime.now()
                })
                
                logger.info(f"广播完成: {event_type.value}, 目标={len(target_sockets)}, 成功={successful_count}, 失败={failed_count}")
                
                return {
                    'success': True,
                    'target_count': len(target_sockets),
                    'successful_count': successful_count,
                    'failed_count': failed_count,
                    'event_type': event_type.value
                }
                
        except Exception as e:
            logger.error(f"广播失败: {e}")
            self.stats['failed_broadcasts'] += 1
            return {
                'success': False,
                'error': str(e),
                'event_type': event_type.value
            }
    
    def _get_target_sockets(self, event_type: BroadcastType, room: str, 
                           exclude_sockets: Set[str] = None) -> Set[str]:
        """获取目标Socket列表"""
        # 获取订阅了该事件类型的Socket
        event_subscribers = self._subscribers.get(event_type, set())
        
        # 获取房间内的Socket
        room_subscribers = self._room_subscribers.get(room, set())
        
        # 取交集
        target_sockets = event_subscribers & room_subscribers
        
        # 排除指定的Socket
        if exclude_sockets:
            target_sockets -= exclude_sockets
        
        # 过滤掉已断开的连接
        active_sockets = set()
        for socket_id in target_sockets:
            if socket_id in self._socket_subscribers:
                # 更新最后活动时间
                self._socket_subscribers[socket_id]['last_activity'] = datetime.now()
                active_sockets.add(socket_id)
        
        return active_sockets
    
    def _send_to_socket(self, socket_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送数据到指定Socket
        
        Args:
            socket_id: Socket ID
            data: 发送的数据
            
        Returns:
            发送结果
        """
        try:
            # 这里应该调用实际的Socket发送方法
            # 在实际实现中，这里会调用Flask-SocketIO的emit方法
            # 目前返回模拟结果
            
            if socket_id in self._socket_subscribers:
                # 模拟发送成功
                logger.debug(f"发送到Socket {socket_id}: {data.get('type', 'unknown')}")
                return {'success': True, 'socket_id': socket_id}
            else:
                # Socket不存在或已断开
                logger.warning(f"Socket不存在: {socket_id}")
                return {'success': False, 'error': 'Socket不存在', 'socket_id': socket_id}
                
        except Exception as e:
            logger.error(f"发送到Socket失败: {socket_id}, {e}")
            return {'success': False, 'error': str(e), 'socket_id': socket_id}
    
    def get_subscribers_info(self, room: str = None) -> Dict[str, Any]:
        """获取订阅者信息"""
        with self._lock:
            if room:
                # 获取特定房间的订阅者
                room_sockets = self._room_subscribers.get(room, set())
                subscribers = {
                    socket_id: self._socket_subscribers[socket_id]
                    for socket_id in room_sockets
                    if socket_id in self._socket_subscribers
                }
            else:
                # 获取所有订阅者
                subscribers = dict(self._socket_subscribers)
            
            return {
                'total_subscribers': len(subscribers),
                'subscribers': subscribers,
                'rooms': {room: len(sockets) for room, sockets in self._room_subscribers.items()},
                'event_subscriptions': {
                    event_type.value: len(sockets) 
                    for event_type, sockets in self._subscribers.items()
                }
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取广播统计信息"""
        with self._lock:
            return {
                **self.stats,
                'active_subscribers': len(self._socket_subscribers),
                'active_rooms': len(self._room_subscribers),
                'success_rate': (
                    self.stats['successful_broadcasts'] / 
                    max(self.stats['total_broadcasts'], 1) * 100
                )
            }
    
    def get_broadcast_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取广播历史"""
        with self._lock:
            history = list(self._broadcast_history)
            return history[-limit:] if limit > 0 else history
    
    def cleanup_inactive_subscribers(self, inactive_threshold: int = 300) -> int:
        """
        清理不活跃的订阅者
        
        Args:
            inactive_threshold: 不活跃阈值（秒）
            
        Returns:
            清理的订阅者数量
        """
        try:
            with self._lock:
                current_time = datetime.now()
                inactive_sockets = []
                
                for socket_id, subscriber_info in self._socket_subscribers.items():
                    last_activity = subscriber_info.get('last_activity', subscriber_info['subscribe_time'])
                    inactive_duration = (current_time - last_activity).total_seconds()
                    
                    if inactive_duration > inactive_threshold:
                        inactive_sockets.append(socket_id)
                
                # 清理不活跃的订阅者
                cleaned_count = 0
                for socket_id in inactive_sockets:
                    if self.unsubscribe(socket_id):
                        cleaned_count += 1
                
                if cleaned_count > 0:
                    logger.info(f"清理了 {cleaned_count} 个不活跃的订阅者")
                
                return cleaned_count
                
        except Exception as e:
            logger.error(f"清理不活跃订阅者失败: {e}")
            return 0
    
    def reset_stats(self):
        """重置统计信息"""
        with self._lock:
            self.stats = {
                'total_broadcasts': 0,
                'successful_broadcasts': 0,
                'failed_broadcasts': 0,
                'subscribers_count': len(self._socket_subscribers),
                'last_broadcast_time': None,
                'broadcast_types': defaultdict(int)
            }
            self._broadcast_history.clear()
            logger.info("广播管理器统计信息已重置")
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"BroadcastManager(subscribers={len(self._socket_subscribers)}, broadcasts={self.stats['total_broadcasts']})"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"BroadcastManager(subscribers={len(self._socket_subscribers)}, "
                f"rooms={len(self._room_subscribers)}, "
                f"total_broadcasts={self.stats['total_broadcasts']})")


class BroadcastManagerSingleton:
    """广播管理器单例"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.broadcast_manager = BroadcastManager()
            self._initialized = True
    
    def get_broadcast_manager(self) -> BroadcastManager:
        """获取广播管理器实例"""
        return self.broadcast_manager
    
    @classmethod
    def get_instance(cls) -> 'BroadcastManagerSingleton':
        """获取单例实例"""
        return cls()


def get_broadcast_manager() -> BroadcastManager:
    """获取全局广播管理器实例的便捷函数"""
    return BroadcastManagerSingleton.get_instance().get_broadcast_manager()


class SocketIOBroadcastAdapter:
    """Flask-SocketIO广播适配器"""
    
    def __init__(self, socketio_instance, broadcast_manager: BroadcastManager = None):
        """
        初始化适配器
        
        Args:
            socketio_instance: Flask-SocketIO实例
            broadcast_manager: 广播管理器实例
        """
        self.socketio = socketio_instance
        self.broadcast_manager = broadcast_manager or get_broadcast_manager()
        
        # 重写广播管理器的发送方法
        self.broadcast_manager._send_to_socket = self._send_to_socket_impl
    
    def _send_to_socket_impl(self, socket_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """实际的Socket发送实现"""
        try:
            # 使用Flask-SocketIO发送数据
            self.socketio.emit(
                'broadcast_message',
                data,
                room=socket_id
            )
            
            logger.debug(f"SocketIO发送成功: {socket_id} -> {data.get('type', 'unknown')}")
            return {'success': True, 'socket_id': socket_id}
            
        except Exception as e:
            logger.error(f"SocketIO发送失败: {socket_id}, {e}")
            return {'success': False, 'error': str(e), 'socket_id': socket_id}
    
    def handle_connect(self, socket_id: str, username: str = None, room: str = "main"):
        """处理Socket连接"""
        return self.broadcast_manager.subscribe(socket_id, username, room)
    
    def handle_disconnect(self, socket_id: str):
        """处理Socket断开"""
        return self.broadcast_manager.unsubscribe(socket_id)
    
    def handle_join_room(self, socket_id: str, room: str):
        """处理加入房间"""
        # 先取消当前订阅，再重新订阅到新房间
        if socket_id in self.broadcast_manager._socket_subscribers:
            subscriber_info = self.broadcast_manager._socket_subscribers[socket_id]
            username = subscriber_info.get('username')
            event_types = subscriber_info.get('event_types')
            
            self.broadcast_manager.unsubscribe(socket_id)
            return self.broadcast_manager.subscribe(socket_id, username, room, event_types)
        
        return False
    
    def handle_leave_room(self, socket_id: str):
        """处理离开房间"""
        return self.broadcast_manager.unsubscribe(socket_id)