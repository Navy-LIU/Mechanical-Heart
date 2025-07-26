"""
用户管理组件
处理用户会话、加入/离开逻辑和在线用户列表维护
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

from models.user import User, create_user
from models.chat_room import get_chat_room
from models.message import create_system_message

# 配置日志
logger = logging.getLogger(__name__)


class UserManager:
    """用户管理器"""
    
    def __init__(self):
        """初始化用户管理器"""
        self.chat_room = get_chat_room()
        self._session_to_socket = {}  # session_id -> socket_id 映射
        self._socket_to_session = {}  # socket_id -> session_id 映射
    
    def add_user(self, session_id: str, username: str, socket_id: str = None) -> Tuple[bool, str, Optional[User]]:
        """
        添加用户到聊天室
        
        Args:
            session_id: 会话ID
            username: 用户名
            socket_id: Socket连接ID（可选）
            
        Returns:
            (成功标志, 消息, 用户对象)
        """
        try:
            # 验证输入参数
            if not session_id or not username:
                return False, "会话ID和用户名不能为空", None
            
            # 检查用户名是否有效
            if not User.is_valid_username(username):
                return False, "用户名格式无效", None
            
            # 检查是否已经在线
            if self.is_user_online_by_session(session_id):
                existing_user = self.chat_room.get_user_by_session(session_id)
                return False, f"会话已存在，用户 {existing_user.username} 已在线", existing_user
            
            # 检查用户名是否被占用
            if self.is_username_taken(username):
                return False, "用户名已被占用", None
            
            # 检查用户数量限制
            if not self._can_add_more_users():
                return False, "聊天室已满", None
            
            # 创建用户
            user = create_user(session_id, username)
            
            # 添加到聊天室
            if self.chat_room.add_user(user):
                # 记录Socket映射
                if socket_id:
                    self._session_to_socket[session_id] = socket_id
                    self._socket_to_session[socket_id] = session_id
                
                logger.info(f"用户 {username} (session: {session_id}) 加入聊天室")
                return True, f"欢迎 {username} 加入聊天室！", user
            else:
                return False, "加入聊天室失败", None
                
        except Exception as e:
            logger.error(f"添加用户失败: {e}")
            return False, f"系统错误: {str(e)}", None
    
    def remove_user(self, session_id: str) -> Tuple[bool, str, Optional[User]]:
        """
        从聊天室移除用户
        
        Args:
            session_id: 会话ID
            
        Returns:
            (成功标志, 消息, 被移除的用户对象)
        """
        try:
            if not session_id:
                return False, "会话ID不能为空", None
            
            # 获取用户信息
            user = self.chat_room.get_user_by_session(session_id)
            if not user:
                return False, "用户不存在", None
            
            # 不能移除AI用户
            if user.is_ai:
                return False, "不能移除AI用户", None
            
            # 从聊天室移除
            removed_user = self.chat_room.remove_user(session_id)
            if removed_user:
                # 清理Socket映射
                socket_id = self._session_to_socket.pop(session_id, None)
                if socket_id:
                    self._socket_to_session.pop(socket_id, None)
                
                logger.info(f"用户 {removed_user.username} (session: {session_id}) 离开聊天室")
                return True, f"{removed_user.username} 已离开聊天室", removed_user
            else:
                return False, "移除用户失败", None
                
        except Exception as e:
            logger.error(f"移除用户失败: {e}")
            return False, f"系统错误: {str(e)}", None
    
    def remove_user_by_socket(self, socket_id: str) -> Tuple[bool, str, Optional[User]]:
        """
        根据Socket ID移除用户
        
        Args:
            socket_id: Socket连接ID
            
        Returns:
            (成功标志, 消息, 被移除的用户对象)
        """
        session_id = self._socket_to_session.get(socket_id)
        if session_id:
            return self.remove_user(session_id)
        else:
            return False, "Socket连接不存在", None
    
    def get_user_by_session(self, session_id: str) -> Optional[User]:
        """根据会话ID获取用户"""
        return self.chat_room.get_user_by_session(session_id)
    
    def get_user_by_socket(self, socket_id: str) -> Optional[User]:
        """根据Socket ID获取用户"""
        session_id = self._socket_to_session.get(socket_id)
        if session_id:
            return self.chat_room.get_user_by_session(session_id)
        return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return self.chat_room.get_user_by_username(username)
    
    def get_online_users(self) -> List[Dict[str, Any]]:
        """获取在线用户列表（公开信息）"""
        return self.chat_room.get_online_users()
    
    def get_online_user_count(self) -> int:
        """获取在线用户数量"""
        return self.chat_room.get_online_user_count()
    
    def is_username_taken(self, username: str) -> bool:
        """检查用户名是否已被占用"""
        return self.chat_room.is_username_taken(username)
    
    def is_user_online_by_session(self, session_id: str) -> bool:
        """检查用户是否在线（根据会话ID）"""
        return self.chat_room.get_user_by_session(session_id) is not None
    
    def is_user_online_by_username(self, username: str) -> bool:
        """检查用户是否在线（根据用户名）"""
        return self.chat_room.is_user_online(username)
    
    def is_user_online_by_socket(self, socket_id: str) -> bool:
        """检查用户是否在线（根据Socket ID）"""
        return socket_id in self._socket_to_session
    
    def get_session_by_socket(self, socket_id: str) -> Optional[str]:
        """根据Socket ID获取会话ID"""
        return self._socket_to_session.get(socket_id)
    
    def get_socket_by_session(self, session_id: str) -> Optional[str]:
        """根据会话ID获取Socket ID"""
        return self._session_to_socket.get(session_id)
    
    def update_socket_mapping(self, session_id: str, socket_id: str) -> bool:
        """更新Socket映射"""
        try:
            # 清理旧的映射
            old_socket = self._session_to_socket.get(session_id)
            if old_socket:
                self._socket_to_session.pop(old_socket, None)
            
            old_session = self._socket_to_session.get(socket_id)
            if old_session:
                self._session_to_socket.pop(old_session, None)
            
            # 建立新映射
            self._session_to_socket[session_id] = socket_id
            self._socket_to_session[socket_id] = session_id
            
            return True
        except Exception as e:
            logger.error(f"更新Socket映射失败: {e}")
            return False
    
    def cleanup_socket_mapping(self, socket_id: str) -> bool:
        """清理Socket映射"""
        try:
            session_id = self._socket_to_session.pop(socket_id, None)
            if session_id:
                self._session_to_socket.pop(session_id, None)
            return True
        except Exception as e:
            logger.error(f"清理Socket映射失败: {e}")
            return False
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """获取用户统计信息"""
        stats = self.chat_room.get_chat_statistics()
        return {
            'total_online_users': stats['online_users'],
            'regular_users': stats['online_users'] - 1,  # 减去AI用户
            'ai_users': 1,
            'socket_connections': len(self._socket_to_session),
            'session_mappings': len(self._session_to_socket)
        }
    
    def validate_user_session(self, session_id: str, username: str) -> Tuple[bool, str]:
        """
        验证用户会话
        
        Args:
            session_id: 会话ID
            username: 用户名
            
        Returns:
            (验证结果, 消息)
        """
        try:
            user = self.get_user_by_session(session_id)
            if not user:
                return False, "会话不存在"
            
            if user.username != username:
                return False, "用户名不匹配"
            
            return True, "会话验证成功"
            
        except Exception as e:
            logger.error(f"验证用户会话失败: {e}")
            return False, f"验证失败: {str(e)}"
    
    def get_user_join_time(self, session_id: str) -> Optional[datetime]:
        """获取用户加入时间"""
        user = self.get_user_by_session(session_id)
        return user.join_time if user else None
    
    def get_user_display_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取用户显示信息"""
        user = self.get_user_by_session(session_id)
        if user:
            return {
                'username': user.username,
                'display_name': user.get_display_name(),
                'is_ai': user.is_ai,
                'join_time': user.join_time.isoformat(),
                'online_duration': (datetime.now() - user.join_time).total_seconds()
            }
        return None
    
    def broadcast_user_list_update(self) -> Dict[str, Any]:
        """获取用于广播的用户列表更新数据"""
        return {
            'type': 'users_update',
            'users': self.get_online_users(),
            'count': self.get_online_user_count(),
            'timestamp': datetime.now().isoformat()
        }
    
    def _can_add_more_users(self) -> bool:
        """检查是否可以添加更多用户"""
        current_count = self.chat_room.get_online_user_count()
        max_users = self.chat_room.max_users
        return current_count < max_users
    
    def _cleanup_inactive_sessions(self) -> int:
        """清理不活跃的会话（预留接口）"""
        # 这里可以实现清理逻辑，比如清理长时间无活动的会话
        # 目前返回0表示没有清理任何会话
        return 0
    
    def get_all_socket_mappings(self) -> Dict[str, Any]:
        """获取所有Socket映射（调试用）"""
        return {
            'session_to_socket': dict(self._session_to_socket),
            'socket_to_session': dict(self._socket_to_session),
            'mapping_count': len(self._session_to_socket)
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"UserManager(users={self.get_online_user_count()}, sockets={len(self._socket_to_session)})"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"UserManager(online_users={self.get_online_user_count()}, "
                f"socket_connections={len(self._socket_to_session)}, "
                f"session_mappings={len(self._session_to_socket)})")


class UserSessionManager:
    """用户会话管理器（单例模式）"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.user_manager = UserManager()
            self._initialized = True
    
    def get_user_manager(self) -> UserManager:
        """获取用户管理器实例"""
        return self.user_manager
    
    @classmethod
    def get_instance(cls) -> 'UserSessionManager':
        """获取会话管理器实例"""
        return cls()


def get_user_manager() -> UserManager:
    """获取全局用户管理器实例的便捷函数"""
    return UserSessionManager.get_instance().get_user_manager()


class UserEventHandler:
    """用户事件处理器"""
    
    def __init__(self, user_manager: UserManager):
        self.user_manager = user_manager
        self.chat_room = user_manager.chat_room
    
    def handle_user_join(self, session_id: str, username: str, socket_id: str = None) -> Dict[str, Any]:
        """
        处理用户加入事件
        
        Returns:
            事件处理结果
        """
        success, message, user = self.user_manager.add_user(session_id, username, socket_id)
        
        result = {
            'success': success,
            'message': message,
            'user': user.to_public_dict() if user else None,
            'timestamp': datetime.now().isoformat()
        }
        
        if success:
            # 添加成功后的额外信息
            result.update({
                'users_update': self.user_manager.broadcast_user_list_update(),
                'welcome_message': f"欢迎 {username} 加入AI聊天室！"
            })
        
        return result
    
    def handle_user_leave(self, session_id: str) -> Dict[str, Any]:
        """
        处理用户离开事件
        
        Returns:
            事件处理结果
        """
        success, message, user = self.user_manager.remove_user(session_id)
        
        result = {
            'success': success,
            'message': message,
            'user': user.to_public_dict() if user else None,
            'timestamp': datetime.now().isoformat()
        }
        
        if success:
            # 离开成功后的额外信息
            result.update({
                'users_update': self.user_manager.broadcast_user_list_update(),
                'goodbye_message': f"{user.username} 离开了聊天室"
            })
        
        return result
    
    def handle_socket_disconnect(self, socket_id: str) -> Dict[str, Any]:
        """
        处理Socket断开事件
        
        Returns:
            事件处理结果
        """
        success, message, user = self.user_manager.remove_user_by_socket(socket_id)
        
        # 清理Socket映射
        self.user_manager.cleanup_socket_mapping(socket_id)
        
        result = {
            'success': success,
            'message': message,
            'user': user.to_public_dict() if user else None,
            'socket_id': socket_id,
            'timestamp': datetime.now().isoformat()
        }
        
        if success:
            result.update({
                'users_update': self.user_manager.broadcast_user_list_update(),
                'disconnect_message': f"{user.username} 断开连接"
            })
        
        return result