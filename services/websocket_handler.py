"""
WebSocket处理器组件
整合所有服务组件，提供统一的WebSocket事件处理接口
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid

from models.user import User
from models.message import Message
from services.user_manager import UserManager, get_user_manager
from services.message_handler import MessageHandler, get_message_handler
from services.chat_history import ChatHistory, get_chat_history
from services.broadcast_manager import BroadcastManager, BroadcastType, get_broadcast_manager

# 配置日志
logger = logging.getLogger(__name__)


class WebSocketHandler:
    """WebSocket事件处理器"""
    
    def __init__(self, broadcast_adapter=None):
        """初始化WebSocket处理器"""
        self.user_manager = get_user_manager()
        self.message_handler = get_message_handler()
        self.chat_history = get_chat_history()
        
        # 设置广播适配器
        self.broadcast_adapter = broadcast_adapter
        if self.broadcast_adapter:
            # 使用适配器的广播管理器
            self.broadcast_manager = self.broadcast_adapter.broadcast_manager
        else:
            # 使用默认的广播管理器
            self.broadcast_manager = get_broadcast_manager()
        
        # WebSocket连接管理
        self._connections = {}  # socket_id -> 连接信息
        self._connection_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'failed_connections': 0,
            'disconnections': 0,
            'start_time': datetime.now()
        }
        
        logger.info("WebSocket处理器初始化完成")
    
    def handle_connect(self, socket_id: str, client_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理客户端连接
        
        Args:
            socket_id: Socket连接ID
            client_info: 客户端信息
            
        Returns:
            连接处理结果
        """
        try:
            current_time = datetime.now()
            
            # 记录连接信息
            connection_info = {
                'socket_id': socket_id,
                'connect_time': current_time,
                'client_ip': client_info.get('ip', 'unknown') if client_info else 'unknown',
                'user_agent': client_info.get('user_agent', 'unknown') if client_info else 'unknown',
                'session_id': None,  # 用户加入聊天室时设置
                'username': None,
                'last_activity': current_time,
                'ping_count': 0,
                'message_count': 0
            }
            
            self._connections[socket_id] = connection_info
            self._connection_stats['total_connections'] += 1
            self._connection_stats['active_connections'] += 1
            
            logger.info(f"WebSocket连接建立: {socket_id}")
            
            # 自动为新连接分配用户ID
            user_id = self.user_manager.generate_user_id(connection_info['client_ip'])
            connection_info['user_id'] = user_id
            
            return {
                'success': True,
                'socket_id': socket_id,
                'user_id': user_id,  # 返回新分配的用户ID
                'server_time': current_time.isoformat(),
                'connection_info': {
                    'socket_id': socket_id,
                    'user_id': user_id,
                    'server_time': current_time.isoformat(),
                    'active_users': len(self.user_manager.get_online_users())
                }
            }
            
        except Exception as e:
            logger.error(f"连接处理失败: {e}")
            self._connection_stats['failed_connections'] += 1
            return {
                'success': False,
                'error': f"连接处理失败: {str(e)}"
            }
    
    def handle_disconnect(self, socket_id: str) -> Dict[str, Any]:
        """
        处理客户端断开连接
        
        Args:
            socket_id: Socket连接ID
            
        Returns:
            断开连接处理结果
        """
        try:
            # 移除用户（如果已加入聊天室）
            success, message, removed_user = self.user_manager.remove_user_by_socket(socket_id)
            
            # 如果成功移除用户，发送离开通知
            if success and removed_user:
                # 广播用户离开事件
                self.broadcast_manager.broadcast_user_leave(
                    username=removed_user.username,
                    user_info=removed_user.to_dict(),
                    room="main"
                )
                
                # 广播更新的用户列表
                self.broadcast_manager.broadcast_user_list_update(
                    users=self.user_manager.get_online_users(),
                    user_count=self.user_manager.get_online_user_count(),
                    room="main"
                )
            
            # 取消广播订阅
            self.broadcast_manager.unsubscribe(socket_id)
            
            # 移除连接记录
            if socket_id in self._connections:
                del self._connections[socket_id]
                self._connection_stats['active_connections'] -= 1
                self._connection_stats['disconnections'] += 1
            
            logger.info(f"WebSocket连接断开: {socket_id}")
            
            return {
                'success': True,
                'message': message,
                'removed_user': removed_user.to_dict() if removed_user else None
            }
            
        except Exception as e:
            logger.error(f"断开连接处理失败: {e}")
            return {
                'success': False,
                'error': f"断开连接处理失败: {str(e)}"
            }
    
    def handle_join_room(self, socket_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理用户加入聊天室
        
        Args:
            socket_id: Socket连接ID
            data: 包含username等信息的数据
            
        Returns:
            加入聊天室处理结果
        """
        try:
            # 获取用户名
            username = data.get('username', '').strip()
            display_name = data.get('display_name', '').strip() or username
            if not username:
                return {
                    'success': False,
                    'error': '用户名不能为空'
                }
            
            # 生成会话ID
            session_id = str(uuid.uuid4())
            
            # 获取连接信息
            connection_info = self._connections.get(socket_id, {})
            user_id = connection_info.get('user_id')  # 使用预分配的用户ID
            ip_address = connection_info.get('client_ip')
            
            # 添加用户到聊天室
            success, message, user = self.user_manager.add_user(
                session_id=session_id,
                username=username, 
                socket_id=socket_id,
                ip_address=ip_address,
                display_name=display_name
            )
            
            # 如果用户对象没有用户ID，使用预分配的
            if user and not user.user_id and user_id:
                user.user_id = user_id
            
            if not success:
                return {
                    'success': False,
                    'error': message
                }
            
            # 更新连接信息
            if socket_id in self._connections:
                self._connections[socket_id].update({
                    'session_id': session_id,
                    'username': username,
                    'last_activity': datetime.now()
                })
            
            # 订阅广播事件
            self.broadcast_manager.subscribe(
                socket_id=socket_id,
                username=username,
                room="main"
            )
            
            # 获取聊天历史
            recent_messages = self.chat_history.get_recent_messages(limit=50)
            history_data = []
            for msg in recent_messages:
                history_data.append({
                    'type': 'message',
                    'username': msg.username,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat(),
                    'is_ai': msg.message_type == 'ai',
                    'is_system': msg.message_type == 'system',
                    'message_id': msg.id
                })
            
            # 创建用户加入系统消息
            system_message_result = self.message_handler.process_system_message(
                f"{username} 加入了聊天室"
            )
            
            # 准备响应数据
            response_data = {
                'success': True,
                'message': message,
                'user': user.to_dict(),
                'session_id': session_id,
                'chat_history': history_data,
                'online_users': self.user_manager.get_online_users(),
                'server_time': datetime.now().isoformat()
            }
            
            # 广播用户加入事件
            if system_message_result['success']:
                self.broadcast_manager.broadcast_user_join(
                    username=username,
                    user_info=user.to_dict(),
                    room="main"
                )
                
                # 广播更新的用户列表
                self.broadcast_manager.broadcast_user_list_update(
                    users=self.user_manager.get_online_users(),
                    user_count=self.user_manager.get_online_user_count(),
                    room="main"
                )
            
            logger.info(f"用户 {username} 加入聊天室成功")
            return response_data
            
        except Exception as e:
            logger.error(f"加入聊天室处理失败: {e}")
            return {
                'success': False,
                'error': f"加入聊天室失败: {str(e)}"
            }
    
    def handle_send_message(self, socket_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理发送消息
        
        Args:
            socket_id: Socket连接ID
            data: 包含message等信息的数据
            
        Returns:
            发送消息处理结果
        """
        try:
            # 获取用户信息
            user = self.user_manager.get_user_by_socket(socket_id)
            if not user:
                return {
                    'success': False,
                    'error': '用户未找到，请重新加入聊天室'
                }
            
            # 获取消息内容
            message_content = data.get('message', '').strip()
            if not message_content:
                return {
                    'success': False,
                    'error': '消息内容不能为空'
                }
            
            # 更新连接活动时间
            if socket_id in self._connections:
                self._connections[socket_id]['last_activity'] = datetime.now()
                self._connections[socket_id]['message_count'] += 1
            
            # 处理消息
            result = self.message_handler.process_message(
                message_content=message_content,
                username=user.username,
                session_id=user.session_id
            )
            
            if not result['success']:
                return {
                    'success': False,
                    'error': result['error']
                }
            
            # 广播消息
            if result['message']:
                # 使用广播管理器的broadcast_message方法
                self.broadcast_manager.broadcast_message(
                    message=result['message'],
                    ai_response=result['ai_response'],
                    room="main"
                )
            
            logger.info(f"消息发送成功: {user.username} -> {message_content[:50]}...")
            
            return {
                'success': True,
                'message': '消息发送成功',
                'message_data': result['message'].to_dict() if result['message'] else None,
                'ai_response': result['ai_response'].to_dict() if result['ai_response'] else None
            }
            
        except Exception as e:
            logger.error(f"发送消息处理失败: {e}")
            return {
                'success': False,
                'error': f"发送消息失败: {str(e)}"
            }
    
    def handle_ping(self, socket_id: str) -> Dict[str, Any]:
        """
        处理心跳检测
        
        Args:
            socket_id: Socket连接ID
            
        Returns:
            心跳处理结果
        """
        try:
            current_time = datetime.now()
            
            # 更新连接活动时间
            if socket_id in self._connections:
                self._connections[socket_id]['last_activity'] = current_time
                self._connections[socket_id]['ping_count'] += 1
            
            return {
                'success': True,
                'timestamp': current_time.timestamp(),
                'server_time': current_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"心跳处理失败: {e}")
            return {
                'success': False,
                'error': f"心跳处理失败: {str(e)}"
            }
    
    def get_server_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        try:
            return {
                'server_name': 'AI Chat Room',
                'version': '1.0.0',
                'start_time': self._connection_stats['start_time'].isoformat(),
                'current_time': datetime.now().isoformat(),
                'active_connections': self._connection_stats['active_connections'],
                'total_users': self.user_manager.get_online_user_count(),
                'total_messages': self.chat_history.get_message_count(),
                'ai_available': self.message_handler.ai_client.is_available()
            }
        except Exception as e:
            logger.error(f"获取服务器信息失败: {e}")
            return {
                'error': f"获取服务器信息失败: {str(e)}"
            }
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        try:
            stats = self._connection_stats.copy()
            stats['current_time'] = datetime.now().isoformat()
            stats['connections'] = []
            
            # 添加当前连接信息（不包含敏感信息）
            for socket_id, conn_info in self._connections.items():
                stats['connections'].append({
                    'socket_id': socket_id,
                    'username': conn_info.get('username'),
                    'connect_time': conn_info['connect_time'].isoformat(),
                    'last_activity': conn_info['last_activity'].isoformat(),
                    'ping_count': conn_info['ping_count'],
                    'message_count': conn_info['message_count']
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"获取连接统计失败: {e}")
            return {
                'error': f"获取连接统计失败: {str(e)}"
            }
    
    def cleanup_inactive_connections(self, timeout_seconds: int = 300) -> int:
        """
        清理不活跃的连接
        
        Args:
            timeout_seconds: 超时时间（秒）
            
        Returns:
            清理的连接数量
        """
        try:
            current_time = datetime.now()
            inactive_sockets = []
            
            for socket_id, conn_info in self._connections.items():
                time_diff = (current_time - conn_info['last_activity']).total_seconds()
                if time_diff > timeout_seconds:
                    inactive_sockets.append(socket_id)
            
            cleanup_count = 0
            for socket_id in inactive_sockets:
                result = self.handle_disconnect(socket_id)
                if result['success']:
                    cleanup_count += 1
            
            if cleanup_count > 0:
                logger.info(f"清理了 {cleanup_count} 个不活跃连接")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"清理不活跃连接失败: {e}")
            return 0