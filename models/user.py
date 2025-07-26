"""
用户数据模型
定义用户的基本属性和行为
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any
import re


@dataclass
class User:
    """用户数据模型"""
    session_id: str
    username: str
    join_time: datetime
    is_ai: bool = False
    user_id: str = None  # 自动分配的唯一用户ID
    ip_address: str = None  # 用户IP地址
    display_name: str = None  # 用户自定义显示名称
    
    def __post_init__(self):
        """初始化后验证"""
        # 如果没有设置display_name，使用username
        if self.display_name is None:
            self.display_name = self.username
        self.validate()
    
    def validate(self) -> None:
        """验证用户数据"""
        if not self.session_id:
            raise ValueError("session_id不能为空")
        
        if not self.username:
            raise ValueError("用户名不能为空")
        
        if not self.is_valid_username(self.username):
            raise ValueError("用户名格式无效")
        
        if not isinstance(self.join_time, datetime):
            raise ValueError("join_time必须是datetime对象")
    
    @staticmethod
    def is_valid_username(username: str) -> bool:
        """验证用户名格式"""
        if not username or not isinstance(username, str):
            return False
        
        # 用户名长度限制
        if len(username) < 1 or len(username) > 20:
            return False
        
        # 用户名只能包含中文、英文、数字、下划线
        pattern = r'^[\u4e00-\u9fa5a-zA-Z0-9_]+$'
        if not re.match(pattern, username):
            return False
        
        # 不能是纯数字
        if username.isdigit():
            return False
        
        # 不能是保留关键词
        reserved_names = {'ai', 'AI', 'admin', 'system', 'bot', 'null', 'undefined'}
        if username.lower() in reserved_names:
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'username': self.username,
            'display_name': self.display_name,
            'join_time': self.join_time.isoformat(),
            'is_ai': self.is_ai,
            'ip_address': self.ip_address
        }
    
    def to_public_dict(self) -> Dict[str, Any]:
        """转换为公开信息字典（不包含敏感信息）"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'display_name': self.display_name,
            'is_ai': self.is_ai,
            'join_time': self.join_time.isoformat()
        }
    
    def is_online(self) -> bool:
        """检查用户是否在线（基于session_id存在）"""
        # 在实际应用中，这里会检查session是否仍然有效
        # 目前简单返回True，表示如果User对象存在就认为在线
        return bool(self.session_id)
    
    def get_display_name(self) -> str:
        """获取显示名称"""
        display = self.display_name or self.username
        if self.is_ai:
            return f"{display} (AI)"
        return display
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"User(username='{self.username}', is_ai={self.is_ai})"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"User(session_id='{self.session_id}', username='{self.username}', "
                f"join_time={self.join_time}, is_ai={self.is_ai})")
    
    def __eq__(self, other) -> bool:
        """相等性比较"""
        if not isinstance(other, User):
            return False
        return self.session_id == other.session_id
    
    def __hash__(self) -> int:
        """哈希值（基于session_id）"""
        return hash(self.session_id)


class AIUser(User):
    """AI用户特殊类"""
    
    def __init__(self, username: str = "AI助手"):
        """初始化AI用户"""
        super().__init__(
            session_id="ai_user_session",
            username=username,
            join_time=datetime.now(),
            is_ai=True
        )
    
    def validate(self) -> None:
        """AI用户的特殊验证"""
        # AI用户允许使用保留关键词
        if not self.session_id:
            raise ValueError("session_id不能为空")
        
        if not self.username:
            raise ValueError("用户名不能为空")
        
        if len(self.username) > 20:
            raise ValueError("用户名长度不能超过20个字符")
        
        if not isinstance(self.join_time, datetime):
            raise ValueError("join_time必须是datetime对象")
    
    def is_online(self) -> bool:
        """AI用户始终在线"""
        return True


def create_user(session_id: str, username: str, user_id: str = None, 
               ip_address: str = None, display_name: str = None) -> User:
    """创建普通用户的工厂函数"""
    return User(
        session_id=session_id,
        username=username,
        join_time=datetime.now(),
        is_ai=False,
        user_id=user_id,
        ip_address=ip_address,
        display_name=display_name
    )


def create_ai_user(username: str = "AI助手") -> AIUser:
    """创建AI用户的工厂函数"""
    return AIUser(username)