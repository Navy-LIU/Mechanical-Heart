"""
聊天室状态模型
管理聊天室的全局状态，包括在线用户和消息历史
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import deque
import threading

from .user import User, AIUser, create_ai_user
from .message import Message, create_system_message


@dataclass
class ChatRoomState:
    """聊天室状态模型"""
    online_users: Dict[str, User] = field(default_factory=dict)
    message_history: deque = field(default_factory=lambda: deque(maxlen=100))
    ai_user: AIUser = field(default_factory=lambda: create_ai_user("AI助手"))
    max_users: int = 100
    max_message_history: int = 100
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False)
    
    def __post_init__(self):
        """初始化后处理"""
        # 确保AI用户在用户列表中
        self.online_users[self.ai_user.session_id] = self.ai_user
        
        # 添加欢迎消息
        welcome_msg = create_system_message("欢迎来到AI聊天室！使用@AI来与AI助手对话。")
        self.message_history.append(welcome_msg)
    
    def add_user(self, user: User) -> bool:
        """添加用户到聊天室"""
        with self._lock:
            # 检查用户数量限制
            if len(self.online_users) >= self.max_users:
                return False
            
            # 检查用户名是否已存在（排除AI用户）
            if self.is_username_taken(user.username) and not user.is_ai:
                return False
            
            # 添加用户
            self.online_users[user.session_id] = user
            
            # 添加系统消息通知
            if not user.is_ai:
                join_msg = create_system_message(f"{user.username} 加入了聊天室")
                self.add_message(join_msg)
            
            return True
    
    def remove_user(self, session_id: str) -> Optional[User]:
        """从聊天室移除用户"""
        with self._lock:
            # 不能移除AI用户
            if session_id == self.ai_user.session_id:
                return None
            
            user = self.online_users.pop(session_id, None)
            if user:
                # 添加系统消息通知
                leave_msg = create_system_message(f"{user.username} 离开了聊天室")
                self.add_message(leave_msg)
            
            return user
    
    def get_user_by_session(self, session_id: str) -> Optional[User]:
        """根据session_id获取用户"""
        with self._lock:
            return self.online_users.get(session_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        with self._lock:
            for user in self.online_users.values():
                if user.username == username:
                    return user
            return None
    
    def is_username_taken(self, username: str) -> bool:
        """检查用户名是否已被占用"""
        with self._lock:
            for user in self.online_users.values():
                if user.username == username:
                    return True
            return False
    
    def get_online_users(self) -> List[Dict[str, Any]]:
        """获取在线用户列表（公开信息）"""
        with self._lock:
            users = []
            # AI用户排在第一位
            if self.ai_user.session_id in self.online_users:
                users.append(self.ai_user.to_public_dict())
            
            # 其他用户按加入时间排序
            other_users = [
                user for user in self.online_users.values() 
                if not user.is_ai
            ]
            other_users.sort(key=lambda u: u.join_time)
            
            for user in other_users:
                users.append(user.to_public_dict())
            
            return users
    
    def get_online_user_count(self) -> int:
        """获取在线用户数量"""
        with self._lock:
            return len(self.online_users)
    
    def add_message(self, message: Message) -> None:
        """添加消息到历史记录"""
        with self._lock:
            self.message_history.append(message)
    
    def get_recent_messages(self, limit: int = 50) -> List[Message]:
        """获取最近的消息"""
        with self._lock:
            messages = list(self.message_history)
            return messages[-limit:] if limit > 0 else messages
    
    def get_messages_by_user(self, username: str, limit: int = 20) -> List[Message]:
        """获取指定用户的消息"""
        with self._lock:
            user_messages = [
                msg for msg in self.message_history 
                if msg.username == username
            ]
            return user_messages[-limit:] if limit > 0 else user_messages
    
    def get_ai_mentioned_messages(self, limit: int = 10) -> List[Message]:
        """获取提及AI的消息"""
        with self._lock:
            ai_messages = [
                msg for msg in self.message_history 
                if msg.mentions_ai
            ]
            return ai_messages[-limit:] if limit > 0 else ai_messages
    
    def clear_message_history(self) -> None:
        """清空消息历史（保留欢迎消息）"""
        with self._lock:
            self.message_history.clear()
            welcome_msg = create_system_message("消息历史已清空。")
            self.message_history.append(welcome_msg)
    
    def get_chat_statistics(self) -> Dict[str, Any]:
        """获取聊天室统计信息"""
        with self._lock:
            total_messages = len(self.message_history)
            user_messages = sum(1 for msg in self.message_history if msg.message_type == 'user')
            ai_messages = sum(1 for msg in self.message_history if msg.message_type == 'ai')
            system_messages = sum(1 for msg in self.message_history if msg.message_type == 'system')
            
            return {
                'online_users': len(self.online_users),
                'total_messages': total_messages,
                'user_messages': user_messages,
                'ai_messages': ai_messages,
                'system_messages': system_messages,
                'ai_mentions': sum(1 for msg in self.message_history if msg.mentions_ai)
            }
    
    def update_ai_user(self, new_ai_user: AIUser) -> None:
        """更新AI用户信息"""
        with self._lock:
            old_session_id = self.ai_user.session_id
            self.online_users.pop(old_session_id, None)
            
            self.ai_user = new_ai_user
            self.online_users[new_ai_user.session_id] = new_ai_user
    
    def is_user_online(self, username: str) -> bool:
        """检查用户是否在线"""
        with self._lock:
            return any(user.username == username for user in self.online_users.values())
    
    def get_user_join_time(self, username: str) -> Optional[datetime]:
        """获取用户加入时间"""
        user = self.get_user_by_username(username)
        return user.join_time if user else None
    
    def broadcast_message_data(self, message: Message) -> Dict[str, Any]:
        """获取用于广播的消息数据"""
        with self._lock:
            return {
                'message': message.format_for_display(),
                'online_users': self.get_online_users(),
                'user_count': self.get_online_user_count(),
                'timestamp': datetime.now().isoformat()
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        with self._lock:
            return {
                'online_users': [user.to_dict() for user in self.online_users.values()],
                'message_count': len(self.message_history),
                'recent_messages': [msg.to_dict() for msg in list(self.message_history)[-10:]],
                'ai_user': self.ai_user.to_dict(),
                'statistics': self.get_chat_statistics()
            }
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"ChatRoom(users={len(self.online_users)}, messages={len(self.message_history)})"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"ChatRoomState(online_users={len(self.online_users)}, "
                f"message_history={len(self.message_history)}, "
                f"max_users={self.max_users})")


class ChatRoomManager:
    """聊天室管理器（单例模式）"""
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
            self.chat_room = ChatRoomState()
            self._initialized = True
    
    def get_chat_room(self) -> ChatRoomState:
        """获取聊天室实例"""
        return self.chat_room
    
    def reset_chat_room(self) -> None:
        """重置聊天室（用于测试）"""
        self.chat_room = ChatRoomState()
    
    @classmethod
    def get_instance(cls) -> 'ChatRoomManager':
        """获取管理器实例"""
        return cls()


def get_chat_room() -> ChatRoomState:
    """获取全局聊天室实例的便捷函数"""
    return ChatRoomManager.get_instance().get_chat_room()


class ChatRoomValidator:
    """聊天室验证器"""
    
    @staticmethod
    def validate_user_limit(current_count: int, max_users: int) -> bool:
        """验证用户数量限制"""
        return current_count < max_users
    
    @staticmethod
    def validate_message_limit(current_count: int, max_messages: int) -> bool:
        """验证消息数量限制"""
        return current_count < max_messages
    
    @staticmethod
    def can_user_join(chat_room: ChatRoomState, username: str) -> tuple[bool, str]:
        """检查用户是否可以加入聊天室"""
        # 检查用户数量限制
        if len(chat_room.online_users) >= chat_room.max_users:
            return False, "聊天室已满"
        
        # 检查用户名是否已被占用
        if chat_room.is_username_taken(username):
            return False, "用户名已被占用"
        
        return True, "可以加入"
    
    @staticmethod
    def validate_chat_room_state(chat_room: ChatRoomState) -> List[str]:
        """验证聊天室状态的完整性"""
        issues = []
        
        # 检查AI用户是否存在
        if not chat_room.ai_user or chat_room.ai_user.session_id not in chat_room.online_users:
            issues.append("AI用户不在在线用户列表中")
        
        # 检查用户数量一致性
        if len(chat_room.online_users) > chat_room.max_users:
            issues.append(f"在线用户数量({len(chat_room.online_users)})超过限制({chat_room.max_users})")
        
        # 检查消息历史长度
        if len(chat_room.message_history) > chat_room.max_message_history:
            issues.append(f"消息历史长度({len(chat_room.message_history)})超过限制({chat_room.max_message_history})")
        
        return issues