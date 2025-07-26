"""
消息处理器组件
处理消息逻辑、验证、格式化和@AI提及检测
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid

from models.message import Message, create_user_message, create_ai_message, create_system_message, MessageValidator
from models.user import User
from services.ai_client import get_ai_client, AIResponseHandler
from services.chat_history import get_chat_history
from services.user_manager import get_user_manager

# 配置日志
logger = logging.getLogger(__name__)


class MessageHandler:
    """消息处理器"""
    
    def __init__(self):
        """初始化消息处理器"""
        self.ai_client = get_ai_client()
        self.ai_response_handler = AIResponseHandler(self.ai_client)
        self.chat_history = get_chat_history()
        self.user_manager = get_user_manager()
        
        # 消息处理统计
        self.stats = {
            'total_messages_processed': 0,
            'user_messages': 0,
            'ai_messages': 0,
            'system_messages': 0,
            'ai_mentions_processed': 0,
            'invalid_messages_rejected': 0,
            'last_processed_time': None
        }
    
    def process_message(self, message_content: str, username: str, session_id: str = None) -> Dict[str, Any]:
        """
        处理用户消息
        
        Args:
            message_content: 消息内容
            username: 用户名
            session_id: 会话ID（可选）
            
        Returns:
            处理结果字典
        """
        try:
            self.stats['total_messages_processed'] += 1
            self.stats['last_processed_time'] = datetime.now()
            
            # 验证消息内容
            validation_result = self._validate_message_content(message_content)
            if not validation_result['valid']:
                self.stats['invalid_messages_rejected'] += 1
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'message': None,
                    'ai_response': None,
                    'broadcast_data': None
                }
            
            # 验证用户
            user_validation = self._validate_user(username, session_id)
            if not user_validation['valid']:
                self.stats['invalid_messages_rejected'] += 1
                return {
                    'success': False,
                    'error': user_validation['error'],
                    'message': None,
                    'ai_response': None,
                    'broadcast_data': None
                }
            
            # 创建用户消息
            user_message = create_user_message(username, message_content)
            self.stats['user_messages'] += 1
            
            # 保存消息到历史
            self.chat_history.add_message(user_message)
            
            # 检查是否需要AI回复
            ai_response = None
            if user_message.mentions_ai:
                ai_response = self._handle_ai_mention(user_message)
                if ai_response:
                    self.stats['ai_mentions_processed'] += 1
                    self.stats['ai_messages'] += 1
                    # 保存AI回复到历史
                    self.chat_history.add_message(ai_response)
            
            # 生成广播数据
            broadcast_data = self._generate_broadcast_data(user_message, ai_response)
            
            logger.info(f"消息处理成功: {username} -> {message_content[:50]}...")
            
            return {
                'success': True,
                'error': None,
                'message': user_message,
                'ai_response': ai_response,
                'broadcast_data': broadcast_data
            }
            
        except Exception as e:
            logger.error(f"消息处理失败: {e}")
            return {
                'success': False,
                'error': f"消息处理异常: {str(e)}",
                'message': None,
                'ai_response': None,
                'broadcast_data': None
            }
    
    def process_system_message(self, content: str) -> Dict[str, Any]:
        """
        处理系统消息
        
        Args:
            content: 系统消息内容
            
        Returns:
            处理结果字典
        """
        try:
            self.stats['total_messages_processed'] += 1
            self.stats['system_messages'] += 1
            self.stats['last_processed_time'] = datetime.now()
            
            # 创建系统消息
            system_message = create_system_message(content)
            
            # 保存到历史
            self.chat_history.add_message(system_message)
            
            # 生成广播数据
            broadcast_data = self._generate_broadcast_data(system_message)
            
            logger.info(f"系统消息处理成功: {content}")
            
            return {
                'success': True,
                'error': None,
                'message': system_message,
                'ai_response': None,
                'broadcast_data': broadcast_data
            }
            
        except Exception as e:
            logger.error(f"系统消息处理失败: {e}")
            return {
                'success': False,
                'error': f"系统消息处理异常: {str(e)}",
                'message': None,
                'ai_response': None,
                'broadcast_data': None
            }
    
    def _validate_message_content(self, content: str) -> Dict[str, Any]:
        """验证消息内容"""
        if not content:
            return {'valid': False, 'error': '消息内容不能为空'}
        
        if not isinstance(content, str):
            return {'valid': False, 'error': '消息内容必须是字符串'}
        
        # 去除首尾空白后检查
        content = content.strip()
        if not content:
            return {'valid': False, 'error': '消息内容不能只包含空白字符'}
        
        # 使用消息验证器验证
        if not MessageValidator.is_valid_content(content):
            return {'valid': False, 'error': '消息内容包含无效字符或格式'}
        
        return {'valid': True, 'error': None}
    
    def _validate_user(self, username: str, session_id: str = None) -> Dict[str, Any]:
        """验证用户"""
        if not username:
            return {'valid': False, 'error': '用户名不能为空'}
        
        # 检查用户是否在线
        if not self.user_manager.is_user_online_by_username(username):
            return {'valid': False, 'error': '用户未在线或不存在'}
        
        # 如果提供了session_id，验证匹配性
        if session_id:
            success, message = self.user_manager.validate_user_session(session_id, username)
            if not success:
                return {'valid': False, 'error': f'用户会话验证失败: {message}'}
        
        return {'valid': True, 'error': None}
    
    def _handle_ai_mention(self, message: Message) -> Optional[Message]:
        """处理AI提及"""
        try:
            # 获取最近的对话上下文
            context_messages = self.chat_history.get_recent_messages(5)
            
            # 处理AI提及
            success, ai_response = self.ai_response_handler.handle_ai_mention(message, context_messages)
            
            if ai_response:
                logger.info(f"AI回复生成: {message.username} -> AI")
                return ai_response
            else:
                logger.warning(f"AI回复生成失败: {message.username}")
                return None
                
        except Exception as e:
            logger.error(f"处理AI提及失败: {e}")
            # 返回错误回复
            error_response = create_ai_message("AI助手", "抱歉，我现在无法回复，请稍后再试。😅")
            return error_response
    
    def _generate_broadcast_data(self, message: Message, ai_response: Message = None) -> Dict[str, Any]:
        """生成广播数据"""
        broadcast_data = {
            'type': 'new_message',
            'message': message.format_for_display(),
            'timestamp': datetime.now().isoformat(),
            'online_users': self.user_manager.get_online_users(),
            'user_count': self.user_manager.get_online_user_count()
        }
        
        # 如果有AI回复，添加到广播数据
        if ai_response:
            broadcast_data['ai_response'] = ai_response.format_for_display()
            broadcast_data['type'] = 'message_with_ai_response'
        
        return broadcast_data
    
    def format_message(self, content: str, username: str, timestamp: datetime = None, message_type: str = 'user') -> Message:
        """
        格式化消息
        
        Args:
            content: 消息内容
            username: 用户名
            timestamp: 时间戳（可选）
            message_type: 消息类型
            
        Returns:
            格式化后的消息对象
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        message_id = str(uuid.uuid4())
        
        return Message(
            id=message_id,
            content=content,
            username=username,
            timestamp=timestamp,
            message_type=message_type
        )
    
    def is_ai_mentioned(self, content: str) -> bool:
        """检测消息中是否提及AI"""
        temp_message = create_user_message("temp_user", content)
        return temp_message.mentions_ai
    
    def extract_ai_mention_content(self, content: str) -> str:
        """提取AI提及的内容"""
        temp_message = create_user_message("temp_user", content)
        return temp_message.extract_ai_mention_content()
    
    def get_message_preview(self, content: str, max_length: int = 50) -> str:
        """获取消息预览"""
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."
    
    def sanitize_message_content(self, content: str) -> str:
        """清理消息内容"""
        return MessageValidator.sanitize_content(content)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取消息处理统计信息"""
        total_processed = max(self.stats['total_messages_processed'], 1)
        
        return {
            **self.stats,
            'ai_mention_rate': (self.stats['ai_mentions_processed'] / total_processed) * 100,
            'rejection_rate': (self.stats['invalid_messages_rejected'] / total_processed) * 100,
            'ai_client_available': self.ai_client.is_available(),
            'ai_client_stats': self.ai_client.get_stats()
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'total_messages_processed': 0,
            'user_messages': 0,
            'ai_messages': 0,
            'system_messages': 0,
            'ai_mentions_processed': 0,
            'invalid_messages_rejected': 0,
            'last_processed_time': None
        }
        logger.info("消息处理器统计信息已重置")
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"MessageHandler(processed={self.stats['total_messages_processed']}, ai_available={self.ai_client.is_available()})"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"MessageHandler(total_processed={self.stats['total_messages_processed']}, "
                f"ai_mentions={self.stats['ai_mentions_processed']}, "
                f"ai_available={self.ai_client.is_available()})")


class MessageProcessor:
    """消息处理器的高级封装"""
    
    def __init__(self):
        """初始化消息处理器"""
        self.message_handler = MessageHandler()
        self.processing_queue = []
        self.max_queue_size = 1000
    
    def process_user_message(self, content: str, username: str, session_id: str = None) -> Dict[str, Any]:
        """处理用户消息的便捷方法"""
        return self.message_handler.process_message(content, username, session_id)
    
    def process_system_notification(self, content: str) -> Dict[str, Any]:
        """处理系统通知的便捷方法"""
        return self.message_handler.process_system_message(content)
    
    def handle_user_join(self, username: str) -> Dict[str, Any]:
        """处理用户加入通知"""
        content = f"{username} 加入了聊天室"
        return self.process_system_notification(content)
    
    def handle_user_leave(self, username: str) -> Dict[str, Any]:
        """处理用户离开通知"""
        content = f"{username} 离开了聊天室"
        return self.process_system_notification(content)
    
    def handle_ai_greeting(self, username: str = None) -> Dict[str, Any]:
        """处理AI问候"""
        greeting_message = self.message_handler.ai_response_handler.get_ai_greeting(username)
        
        # 保存AI问候到历史
        self.message_handler.chat_history.add_message(greeting_message)
        self.message_handler.stats['ai_messages'] += 1
        
        # 生成广播数据
        broadcast_data = self.message_handler._generate_broadcast_data(greeting_message)
        
        return {
            'success': True,
            'error': None,
            'message': greeting_message,
            'ai_response': None,
            'broadcast_data': broadcast_data
        }
    
    def handle_ai_farewell(self, username: str = None) -> Dict[str, Any]:
        """处理AI告别"""
        farewell_message = self.message_handler.ai_response_handler.get_ai_farewell(username)
        
        # 保存AI告别到历史
        self.message_handler.chat_history.add_message(farewell_message)
        self.message_handler.stats['ai_messages'] += 1
        
        # 生成广播数据
        broadcast_data = self.message_handler._generate_broadcast_data(farewell_message)
        
        return {
            'success': True,
            'error': None,
            'message': farewell_message,
            'ai_response': None,
            'broadcast_data': broadcast_data
        }
    
    def validate_message_before_processing(self, content: str, username: str) -> Tuple[bool, str]:
        """在处理前验证消息"""
        # 验证内容
        content_validation = self.message_handler._validate_message_content(content)
        if not content_validation['valid']:
            return False, content_validation['error']
        
        # 验证用户
        user_validation = self.message_handler._validate_user(username)
        if not user_validation['valid']:
            return False, user_validation['error']
        
        return True, "验证通过"
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        handler_stats = self.message_handler.get_stats()
        
        return {
            **handler_stats,
            'queue_size': len(self.processing_queue),
            'max_queue_size': self.max_queue_size,
            'queue_usage': (len(self.processing_queue) / self.max_queue_size) * 100
        }
    
    def clear_processing_queue(self):
        """清空处理队列"""
        self.processing_queue.clear()
        logger.info("消息处理队列已清空")
    
    def reset_all_stats(self):
        """重置所有统计信息"""
        self.message_handler.reset_stats()
        self.clear_processing_queue()


class MessageHandlerManager:
    """消息处理器管理器（单例模式）"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.message_processor = MessageProcessor()
            self._initialized = True
    
    def get_message_processor(self) -> MessageProcessor:
        """获取消息处理器实例"""
        return self.message_processor
    
    def get_message_handler(self) -> MessageHandler:
        """获取底层消息处理器实例"""
        return self.message_processor.message_handler
    
    @classmethod
    def get_instance(cls) -> 'MessageHandlerManager':
        """获取管理器实例"""
        return cls()


def get_message_processor() -> MessageProcessor:
    """获取全局消息处理器实例的便捷函数"""
    return MessageHandlerManager.get_instance().get_message_processor()


def get_message_handler() -> MessageHandler:
    """获取全局消息处理器实例的便捷函数"""
    return MessageHandlerManager.get_instance().get_message_handler()


class MessageBatchProcessor:
    """批量消息处理器"""
    
    def __init__(self, message_handler: MessageHandler):
        self.message_handler = message_handler
        self.batch_size = 10
        self.batch_timeout = 5.0  # 秒
    
    def process_message_batch(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量处理消息"""
        results = []
        
        for msg_data in messages:
            try:
                if msg_data.get('type') == 'user':
                    result = self.message_handler.process_message(
                        msg_data['content'],
                        msg_data['username'],
                        msg_data.get('session_id')
                    )
                elif msg_data.get('type') == 'system':
                    result = self.message_handler.process_system_message(msg_data['content'])
                else:
                    result = {
                        'success': False,
                        'error': f"未知消息类型: {msg_data.get('type')}",
                        'message': None,
                        'ai_response': None,
                        'broadcast_data': None
                    }
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"批量处理消息失败: {e}")
                results.append({
                    'success': False,
                    'error': f"处理异常: {str(e)}",
                    'message': None,
                    'ai_response': None,
                    'broadcast_data': None
                })
        
        return results
    
    def validate_message_batch(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量验证消息"""
        validation_results = []
        
        for msg_data in messages:
            try:
                content = msg_data.get('content', '')
                username = msg_data.get('username', '')
                
                # 验证内容
                content_validation = self.message_handler._validate_message_content(content)
                if not content_validation['valid']:
                    validation_results.append({
                        'valid': False,
                        'error': content_validation['error'],
                        'message_data': msg_data
                    })
                    continue
                
                # 验证用户
                user_validation = self.message_handler._validate_user(username)
                if not user_validation['valid']:
                    validation_results.append({
                        'valid': False,
                        'error': user_validation['error'],
                        'message_data': msg_data
                    })
                    continue
                
                validation_results.append({
                    'valid': True,
                    'error': None,
                    'message_data': msg_data
                })
                
            except Exception as e:
                validation_results.append({
                    'valid': False,
                    'error': f"验证异常: {str(e)}",
                    'message_data': msg_data
                })
        
        return validation_results