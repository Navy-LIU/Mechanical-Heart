"""
消息数据模型
定义聊天消息的基本属性和行为
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List
import uuid
import re
import html


@dataclass
class Message:
    """消息数据模型"""
    id: str
    content: str
    username: str
    timestamp: datetime
    message_type: str  # 'user', 'ai', 'system'
    mentions_ai: bool = False
    
    def __post_init__(self):
        """初始化后验证和处理"""
        self.validate()
        self.mentions_ai = self.detect_ai_mention()
        # 对内容进行HTML转义以防止XSS攻击
        self.content = html.escape(self.content)
    
    def validate(self) -> None:
        """验证消息数据"""
        if not self.id:
            raise ValueError("消息ID不能为空")
        
        if not self.content:
            raise ValueError("消息内容不能为空")
        
        if not self.username:
            raise ValueError("用户名不能为空")
        
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp必须是datetime对象")
        
        if self.message_type not in ['user', 'ai', 'system']:
            raise ValueError("message_type必须是'user', 'ai', 'system'之一")
        
        # 验证消息长度
        if len(self.content) > 1000:
            raise ValueError("消息内容不能超过1000个字符")
        
        # 验证用户名长度
        if len(self.username) > 20:
            raise ValueError("用户名长度不能超过20个字符")
    
    def detect_ai_mention(self) -> bool:
        """检测消息中是否提及AI"""
        if self.message_type == 'ai' or self.message_type == 'system':
            return False
        
        # 检测@AI的各种形式
        ai_patterns = [
            r'@AI\b',           # @AI
            r'@ai\b',           # @ai
            r'@Ai\b',           # @Ai
            r'@aI\b',           # @aI
            r'@AI助手\b',        # @AI助手
            r'@ai助手\b',        # @ai助手
            r'@智能助手\b',       # @智能助手
            r'@助手\b',          # @助手
        ]
        
        for pattern in ai_patterns:
            if re.search(pattern, self.content):
                return True
        
        return False
    
    def extract_ai_mention_content(self) -> str:
        """提取@AI后的内容作为AI的输入"""
        if not self.mentions_ai:
            return ""
        
        # 移除@AI标记，获取实际要发送给AI的内容
        content = self.content
        
        # 移除各种@AI形式（按长度从长到短排序，避免部分匹配）
        ai_patterns = [
            r'@AI助手\s*',
            r'@ai助手\s*',
            r'@智能助手\s*',
            r'@助手\s*',
            r'@AI\s*',
            r'@ai\s*',
            r'@Ai\s*',
            r'@aI\s*',
        ]
        
        for pattern in ai_patterns:
            if re.search(pattern, content, flags=re.IGNORECASE):
                content = re.sub(pattern, '', content, flags=re.IGNORECASE)
                break  # 只匹配第一个找到的模式
        
        return content.strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'content': self.content,
            'username': self.username,
            'timestamp': self.timestamp.isoformat(),
            'message_type': self.message_type,
            'mentions_ai': self.mentions_ai
        }
    
    def format_for_display(self) -> Dict[str, Any]:
        """格式化为前端显示格式"""
        return {
            'id': self.id,
            'content': self.content,
            'username': self.username,
            'timestamp': self.timestamp.isoformat(),
            'message_type': self.message_type,
            'mentions_ai': self.mentions_ai,
            'formatted_time': self.get_formatted_time(),
            'display_username': self.get_display_username()
        }
    
    def get_formatted_time(self) -> str:
        """获取格式化的时间字符串"""
        return self.timestamp.strftime("%H:%M:%S")
    
    def get_display_username(self) -> str:
        """获取显示用的用户名"""
        if self.message_type == 'ai':
            return f"{self.username} (AI)"
        elif self.message_type == 'system':
            return "系统"
        return self.username
    
    def is_from_ai(self) -> bool:
        """判断是否来自AI"""
        return self.message_type == 'ai'
    
    def is_system_message(self) -> bool:
        """判断是否是系统消息"""
        return self.message_type == 'system'
    
    def get_content_preview(self, max_length: int = 50) -> str:
        """获取内容预览（用于通知等）"""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"Message(username='{self.username}', type='{self.message_type}', content='{self.get_content_preview()}')"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"Message(id='{self.id}', username='{self.username}', "
                f"type='{self.message_type}', timestamp={self.timestamp}, "
                f"mentions_ai={self.mentions_ai})")
    
    def __eq__(self, other) -> bool:
        """相等性比较"""
        if not isinstance(other, Message):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """哈希值（基于消息ID）"""
        return hash(self.id)


def create_user_message(username: str, content: str) -> Message:
    """创建用户消息的工厂函数"""
    return Message(
        id=str(uuid.uuid4()),
        content=content,
        username=username,
        timestamp=datetime.now(),
        message_type='user'
    )


def create_ai_message(ai_username: str, content: str) -> Message:
    """创建AI消息的工厂函数"""
    return Message(
        id=str(uuid.uuid4()),
        content=content,
        username=ai_username,
        timestamp=datetime.now(),
        message_type='ai'
    )


def create_system_message(content: str) -> Message:
    """创建系统消息的工厂函数"""
    return Message(
        id=str(uuid.uuid4()),
        content=content,
        username="系统",
        timestamp=datetime.now(),
        message_type='system'
    )


class MessageValidator:
    """消息验证器"""
    
    @staticmethod
    def is_valid_content(content: str) -> bool:
        """验证消息内容是否有效"""
        if not content or not isinstance(content, str):
            return False
        
        # 检查长度
        if len(content.strip()) == 0 or len(content) > 1000:
            return False
        
        # 检查是否包含恶意内容（简单检查）
        malicious_patterns = [
            r'<script\b',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe\b',
            r'<object\b',
            r'<embed\b'
        ]
        
        for pattern in malicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return False
        
        return True
    
    @staticmethod
    def sanitize_content(content: str) -> str:
        """清理消息内容"""
        if not content:
            return ""
        
        # 去除首尾空白
        content = content.strip()
        
        # HTML转义
        content = html.escape(content)
        
        # 限制长度
        if len(content) > 1000:
            content = content[:1000]
        
        return content
    
    @staticmethod
    def extract_mentions(content: str) -> List[str]:
        """提取消息中的@提及"""
        mentions = []
        
        # 匹配@用户名模式
        pattern = r'@([a-zA-Z0-9_\u4e00-\u9fa5]+)'
        matches = re.findall(pattern, content)
        
        for match in matches:
            if len(match) <= 20:  # 用户名长度限制
                mentions.append(match)
        
        return list(set(mentions))  # 去重


class MessageFormatter:
    """消息格式化器"""
    
    @staticmethod
    def format_for_websocket(message: Message) -> Dict[str, Any]:
        """格式化为WebSocket传输格式"""
        return {
            'id': message.id,
            'content': message.content,
            'username': message.username,
            'timestamp': message.timestamp.isoformat(),
            'message_type': message.message_type,
            'mentions_ai': message.mentions_ai
        }
    
    @staticmethod
    def format_for_api(message: Message) -> Dict[str, Any]:
        """格式化为API响应格式"""
        return {
            'message_id': message.id,
            'text': message.content,
            'sender': message.username,
            'sent_at': message.timestamp.isoformat(),
            'type': message.message_type,
            'ai_mentioned': message.mentions_ai
        }
    
    @staticmethod
    def format_message_list(messages: List[Message]) -> List[Dict[str, Any]]:
        """格式化消息列表"""
        return [msg.format_for_display() for msg in messages]