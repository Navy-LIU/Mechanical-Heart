"""
用户管理组件
处理用户会话、加入/离开逻辑和在线用户列表维护
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
import uuid
import hashlib
from collections import deque

from models.user import User, create_user
from models.chat_room import get_chat_room
from models.message import create_system_message
from services.chat_history import get_chat_history

# 配置日志
logger = logging.getLogger(__name__)


class UserManager:
    """用户管理器"""
    
    def __init__(self):
        """初始化用户管理器"""
        self.chat_room = get_chat_room()
        self._session_to_socket = {}  # session_id -> socket_id 映射
        self._socket_to_session = {}  # socket_id -> session_id 映射
        self._user_ids = set()  # 已分配的用户ID集合
        self._ip_users = {}  # ip_address -> [用户列表] 映射
        self._user_history = deque(maxlen=30)  # 最近30个用户历史记录
        self.MAX_USERS = 30  # 最大用户数量
    
    def generate_user_id(self, ip_address: str = None) -> str:
        """
        生成唯一的用户ID
        
        Args:
            ip_address: 用户IP地址，用于生成更友好的ID
            
        Returns:
            唯一的用户ID
        """
        # 生成基于IP和时间的短编码
        if ip_address:
            # 使用IP地址的最后两段和时间戳
            ip_parts = ip_address.split('.')
            ip_suffix = ''.join(ip_parts[-2:]) if len(ip_parts) >= 2 else ip_address[-4:]
        else:
            ip_suffix = 'xxxx'
        
        # 生成唯一ID直到找到未使用的
        attempt = 0
        while attempt < 1000:  # 防止无限循环
            timestamp_suffix = str(int(datetime.now().timestamp() * 1000))[-6:]  # 6位时间戳
            user_id = f"u{ip_suffix}{timestamp_suffix}{attempt:02d}"
            
            if user_id not in self._user_ids:
                self._user_ids.add(user_id)
                return user_id
            attempt += 1
        
        # 如果无法生成唯一ID，使用UUID
        fallback_id = f"u{str(uuid.uuid4())[:8]}"
        self._user_ids.add(fallback_id)
        return fallback_id
    
    def add_user_to_ip_mapping(self, user: User) -> None:
        """将用户添加到IP映射中"""
        if user.ip_address:
            if user.ip_address not in self._ip_users:
                self._ip_users[user.ip_address] = []
            self._ip_users[user.ip_address].append(user)
    
    def remove_user_from_ip_mapping(self, user: User) -> None:
        """从IP映射中移除用户"""
        if user.ip_address and user.ip_address in self._ip_users:
            try:
                self._ip_users[user.ip_address].remove(user)
                if not self._ip_users[user.ip_address]:
                    del self._ip_users[user.ip_address]
            except ValueError:
                pass  # 用户不在列表中
    
    def get_users_by_ip(self, ip_address: str) -> List[User]:
        """获取指定IP下的所有用户"""
        return self._ip_users.get(ip_address, [])
    
    def get_suggested_username_for_ip(self, ip_address: str) -> Optional[str]:
        """
        为指定IP地址获取建议的用户名（最近使用的可用用户名）
        
        Args:
            ip_address: IP地址
            
        Returns:
            建议的用户名，如果没有则返回None
        """
        if not ip_address:
            return None
            
        try:
            chat_history = get_chat_history()
            # 获取该IP最近使用的用户名列表
            recent_usernames = chat_history.get_recent_usernames_for_ip(ip_address, limit=10)
            
            # 找到第一个当前未被占用的用户名
            for username in recent_usernames:
                if not self.is_username_taken(username):
                    logger.info(f"为IP {ip_address} 找到建议用户名: {username}")
                    return username
            
            return None
            
        except Exception as e:
            logger.error(f"获取IP建议用户名失败: {e}")
            return None
    
    def get_username_suggestions_for_ip(self, ip_address: str, limit: int = 3) -> Dict[str, Any]:
        """
        为指定IP地址获取用户名建议列表
        
        Args:
            ip_address: IP地址
            limit: 返回建议数量限制
            
        Returns:
            包含建议用户名信息的字典
        """
        result = {
            'has_history': False,
            'suggested_username': None,
            'recent_usernames': [],
            'available_usernames': []
        }
        
        if not ip_address:
            return result
            
        try:
            chat_history = get_chat_history()
            # 获取该IP最近使用的用户名列表
            recent_usernames = chat_history.get_recent_usernames_for_ip(ip_address, limit=limit * 2)
            
            if recent_usernames:
                result['has_history'] = True
                result['recent_usernames'] = recent_usernames
                
                # 找到当前可用的用户名
                available_usernames = []
                for username in recent_usernames:
                    if not self.is_username_taken(username):
                        available_usernames.append(username)
                        if len(available_usernames) >= limit:
                            break
                
                result['available_usernames'] = available_usernames
                
                # 设置首选建议用户名
                if available_usernames:
                    result['suggested_username'] = available_usernames[0]
                    logger.info(f"为IP {ip_address} 提供用户名建议: {available_usernames}")
            
            return result
            
        except Exception as e:
            logger.error(f"获取IP用户名建议失败: {e}")
            return result
    
    def add_user(self, session_id: str, username: str, socket_id: str = None, 
                 ip_address: str = None, display_name: str = None) -> Tuple[bool, str, Optional[User]]:
        """
        添加用户到聊天室
        
        Args:
            session_id: 会话ID
            username: 用户名
            socket_id: Socket连接ID（可选）
            ip_address: IP地址（可选）
            display_name: 显示名称（可选）
            
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
            
            # 生成唯一用户ID
            user_id = self.generate_user_id(ip_address)
            
            # 创建用户
            user = create_user(
                session_id=session_id, 
                username=username, 
                user_id=user_id,
                ip_address=ip_address,
                display_name=display_name
            )
            
            # 添加到聊天室
            if self.chat_room.add_user(user):
                # 记录Socket映射
                if socket_id:
                    self._session_to_socket[session_id] = socket_id
                    self._socket_to_session[socket_id] = session_id
                
                # 添加到IP映射
                self.add_user_to_ip_mapping(user)
                
                # 记录IP-用户名关联到数据库
                if ip_address and username:
                    try:
                        chat_history = get_chat_history()
                        chat_history.record_ip_username_usage(ip_address, username)
                        logger.debug(f"IP-用户名关联已记录: {ip_address} -> {username}")
                    except Exception as e:
                        logger.error(f"记录IP-用户名关联失败: {e}")
                
                # 添加到用户历史
                self._user_history.append({
                    'user_id': user.user_id,
                    'username': user.username,
                    'ip_address': user.ip_address,
                    'join_time': user.join_time,
                    'session_id': session_id
                })
                
                logger.info(f"用户 {username} (ID: {user_id}, session: {session_id}, IP: {ip_address}) 加入聊天室")
                return True, f"欢迎 {username} 加入聊天室！您的ID是: {user_id}", user
            else:
                # 如果加入失败，移除已分配的用户ID
                self._user_ids.discard(user_id)
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
                
                # 从IP映射中移除
                self.remove_user_from_ip_mapping(removed_user)
                
                # 移除用户ID记录
                if removed_user.user_id:
                    self._user_ids.discard(removed_user.user_id)
                
                logger.info(f"用户 {removed_user.username} (ID: {removed_user.user_id}, session: {session_id}) 离开聊天室")
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
    
    def update_socket_mapping(self, session_id: str, new_socket_id: str) -> bool:
        """更新Socket映射"""
        try:
            # 移除旧映射
            old_socket_id = self._session_to_socket.get(session_id)
            if old_socket_id:
                self._socket_to_session.pop(old_socket_id, None)
            
            # 建立新映射
            self._session_to_socket[session_id] = new_socket_id
            self._socket_to_session[new_socket_id] = session_id
            
            logger.info(f"更新Socket映射: {session_id} -> {new_socket_id}")
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
            'session_mappings': len(self._session_to_socket),
            'max_users_limit': self.MAX_USERS,
            'user_ids_allocated': len(self._user_ids),
            'unique_ips': len(self._ip_users),
            'user_history_count': len(self._user_history)
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
                'user_id': user.user_id,
                'username': user.username,
                'display_name': user.get_display_name(),
                'is_ai': user.is_ai,
                'join_time': user.join_time.isoformat(),
                'online_duration': (datetime.now() - user.join_time).total_seconds(),
                'ip_address': user.ip_address
            }
        return None
    
    def update_user_display_name(self, session_id: str, new_display_name: str) -> Tuple[bool, str]:
        """
        更新用户显示名称
        
        Args:
            session_id: 会话ID
            new_display_name: 新的显示名称
            
        Returns:
            (成功标志, 消息)
        """
        try:
            user = self.get_user_by_session(session_id)
            if not user:
                return False, "用户不存在"
            
            # 验证新显示名称
            if not new_display_name or len(new_display_name.strip()) == 0:
                return False, "显示名称不能为空"
            
            new_display_name = new_display_name.strip()
            if len(new_display_name) > 20:
                return False, "显示名称不能超过20个字符"
            
            # 检查是否与其他用户的显示名称冲突
            for other_user in self.get_online_users():
                if other_user['session_id'] != session_id and other_user.get('display_name') == new_display_name:
                    return False, "该显示名称已被使用"
            
            # 更新显示名称
            old_display_name = user.display_name
            user.display_name = new_display_name
            
            logger.info(f"用户 {user.username} (ID: {user.user_id}) 显示名称从 '{old_display_name}' 更新为 '{new_display_name}'")
            return True, f"显示名称已更新为: {new_display_name}"
            
        except Exception as e:
            logger.error(f"更新用户显示名称失败: {e}")
            return False, f"系统错误: {str(e)}"
    
    def get_user_history(self) -> List[Dict[str, Any]]:
        """获取用户历史记录"""
        return list(self._user_history)
    
    def get_ip_statistics(self) -> Dict[str, Any]:
        """获取IP统计信息"""
        ip_stats = {}
        for ip, users in self._ip_users.items():
            ip_stats[ip] = {
                'user_count': len(users),
                'usernames': [user.username for user in users],
                'user_ids': [user.user_id for user in users]
            }
        
        return {
            'total_ips': len(self._ip_users),
            'ip_details': ip_stats,
            'max_users_per_ip': max([len(users) for users in self._ip_users.values()]) if self._ip_users else 0
        }
    
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
        current_user_count = self.get_online_user_count()
        return current_user_count < self.MAX_USERS
    
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
        
        return {
            'success': success,
            'message': message,
            'user': user.to_dict() if user else None,
            'event_type': 'user_join',
            'timestamp': datetime.now().isoformat()
        }
    
    def handle_user_leave(self, session_id: str) -> Dict[str, Any]:
        """
        处理用户离开事件
        
        Returns:
            事件处理结果
        """
        success, message, user = self.user_manager.remove_user(session_id)
        
        return {
            'success': success,
            'message': message,
            'user': user.to_dict() if user else None,
            'event_type': 'user_leave',
            'timestamp': datetime.now().isoformat()
        }
    
    def handle_user_reconnect(self, session_id: str, new_socket_id: str) -> Dict[str, Any]:
        """
        处理用户重连事件
        
        Returns:
            事件处理结果
        """
        success = self.user_manager.update_socket_mapping(session_id, new_socket_id)
        user = self.user_manager.get_user_by_session(session_id) if success else None
        
        return {
            'success': success,
            'message': '重连成功' if success else '重连失败',
            'user': user.to_dict() if user else None,
            'event_type': 'user_reconnect',
            'timestamp': datetime.now().isoformat()
        }


def get_user_event_handler() -> UserEventHandler:
    """获取用户事件处理器"""
    return UserEventHandler(get_user_manager())