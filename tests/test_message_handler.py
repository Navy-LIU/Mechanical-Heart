"""
消息处理器单元测试
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from services.message_handler import (
    MessageHandler, MessageProcessor, get_message_processor, get_message_handler,
    MessageBatchProcessor
)
from models.message import create_user_message, create_system_message
from models.chat_room import ChatRoomManager
from services.ai_client import MockAIClient


class TestMessageHandler:
    """消息处理器测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 重置聊天室状态
        ChatRoomManager.get_instance().reset_chat_room()
        
        # 使用模拟AI客户端
        with patch('services.message_handler.get_ai_client') as mock_get_ai_client:
            mock_get_ai_client.return_value = MockAIClient()
            self.message_handler = MessageHandler()
        
        # 添加测试用户
        self.message_handler.user_manager.add_user("session_123", "测试用户", "socket_123")
    
    def test_message_handler_initialization(self):
        """测试消息处理器初始化"""
        assert self.message_handler.ai_client is not None
        assert self.message_handler.ai_response_handler is not None
        assert self.message_handler.chat_history is not None
        assert self.message_handler.user_manager is not None
        
        # 检查初始统计
        stats = self.message_handler.get_stats()
        assert stats['total_messages_processed'] == 0
        assert stats['user_messages'] == 0
        assert stats['ai_messages'] == 0
    
    def test_process_message_success(self):
        """测试成功处理消息"""
        result = self.message_handler.process_message("你好大家！", "测试用户", "session_123")
        
        assert result['success'] is True
        assert result['error'] is None
        assert result['message'] is not None
        assert result['message'].content == "你好大家！"
        assert result['message'].username == "测试用户"
        assert result['message'].message_type == "user"
        assert result['broadcast_data'] is not None
        
        # 检查统计更新
        stats = self.message_handler.get_stats()
        assert stats['total_messages_processed'] == 1
        assert stats['user_messages'] == 1
    
    def test_process_message_with_ai_mention(self):
        """测试处理包含AI提及的消息"""
        result = self.message_handler.process_message("@AI 你好", "测试用户", "session_123")
        
        assert result['success'] is True
        assert result['message'] is not None
        assert result['message'].mentions_ai is True
        assert result['ai_response'] is not None
        assert result['ai_response'].message_type == "ai"
        
        # 检查统计更新
        stats = self.message_handler.get_stats()
        assert stats['total_messages_processed'] == 1
        assert stats['user_messages'] == 1
        assert stats['ai_messages'] == 1
        assert stats['ai_mentions_processed'] == 1
    
    def test_process_message_empty_content(self):
        """测试处理空消息内容"""
        result = self.message_handler.process_message("", "测试用户", "session_123")
        
        assert result['success'] is False
        assert "不能为空" in result['error']
        assert result['message'] is None
        assert result['ai_response'] is None
        
        # 检查统计更新
        stats = self.message_handler.get_stats()
        assert stats['invalid_messages_rejected'] == 1
    
    def test_process_message_whitespace_only(self):
        """测试处理只包含空白字符的消息"""
        result = self.message_handler.process_message("   \n\t   ", "测试用户", "session_123")
        
        assert result['success'] is False
        assert "空白字符" in result['error']
        assert result['message'] is None
    
    def test_process_message_invalid_user(self):
        """测试处理无效用户的消息"""
        result = self.message_handler.process_message("测试消息", "不存在的用户", "invalid_session")
        
        assert result['success'] is False
        assert "未在线" in result['error'] or "不存在" in result['error']
        assert result['message'] is None
    
    def test_process_message_session_mismatch(self):
        """测试会话ID不匹配的情况"""
        result = self.message_handler.process_message("测试消息", "测试用户", "wrong_session")
        
        assert result['success'] is False
        assert "验证失败" in result['error']
        assert result['message'] is None
    
    def test_process_system_message(self):
        """测试处理系统消息"""
        result = self.message_handler.process_system_message("系统通知：服务器维护")
        
        assert result['success'] is True
        assert result['error'] is None
        assert result['message'] is not None
        assert result['message'].content == "系统通知：服务器维护"
        assert result['message'].message_type == "system"
        assert result['broadcast_data'] is not None
        
        # 检查统计更新
        stats = self.message_handler.get_stats()
        assert stats['system_messages'] == 1
    
    def test_validate_message_content(self):
        """测试消息内容验证"""
        # 有效内容
        result = self.message_handler._validate_message_content("正常消息")
        assert result['valid'] is True
        assert result['error'] is None
        
        # 空内容
        result = self.message_handler._validate_message_content("")
        assert result['valid'] is False
        assert "不能为空" in result['error']
        
        # 非字符串内容
        result = self.message_handler._validate_message_content(123)
        assert result['valid'] is False
        assert "必须是字符串" in result['error']
        
        # 只有空白字符
        result = self.message_handler._validate_message_content("   ")
        assert result['valid'] is False
        assert "空白字符" in result['error']
    
    def test_validate_user(self):
        """测试用户验证"""
        # 有效用户
        result = self.message_handler._validate_user("测试用户", "session_123")
        assert result['valid'] is True
        assert result['error'] is None
        
        # 空用户名
        result = self.message_handler._validate_user("", "session_123")
        assert result['valid'] is False
        assert "不能为空" in result['error']
        
        # 不存在的用户
        result = self.message_handler._validate_user("不存在的用户")
        assert result['valid'] is False
        assert "未在线" in result['error'] or "不存在" in result['error']
    
    def test_format_message(self):
        """测试消息格式化"""
        timestamp = datetime.now()
        message = self.message_handler.format_message(
            "测试内容", "测试用户", timestamp, "user"
        )
        
        assert message.content == "测试内容"
        assert message.username == "测试用户"
        assert message.timestamp == timestamp
        assert message.message_type == "user"
        assert message.id is not None
    
    def test_is_ai_mentioned(self):
        """测试AI提及检测"""
        assert self.message_handler.is_ai_mentioned("@AI 你好") is True
        assert self.message_handler.is_ai_mentioned("@ai 帮忙") is True
        assert self.message_handler.is_ai_mentioned("普通消息") is False
        assert self.message_handler.is_ai_mentioned("email@domain.com") is False
    
    def test_extract_ai_mention_content(self):
        """测试提取AI提及内容"""
        content = self.message_handler.extract_ai_mention_content("@AI 今天天气怎么样？")
        assert content == "今天天气怎么样？"
        
        content = self.message_handler.extract_ai_mention_content("普通消息")
        assert content == ""
    
    def test_get_message_preview(self):
        """测试获取消息预览"""
        short_msg = "短消息"
        preview = self.message_handler.get_message_preview(short_msg)
        assert preview == "短消息"
        
        long_msg = "这是一条很长的消息" * 10
        preview = self.message_handler.get_message_preview(long_msg, 20)
        assert len(preview) <= 23  # 20 + "..."
        assert preview.endswith("...")
    
    def test_sanitize_message_content(self):
        """测试清理消息内容"""
        malicious_content = "<script>alert('xss')</script>"
        cleaned = self.message_handler.sanitize_message_content(malicious_content)
        
        assert "<script>" not in cleaned
        assert "&lt;script&gt;" in cleaned
    
    def test_get_stats(self):
        """测试获取统计信息"""
        # 处理一些消息
        self.message_handler.process_message("普通消息", "测试用户", "session_123")
        self.message_handler.process_message("@AI 你好", "测试用户", "session_123")
        self.message_handler.process_system_message("系统通知")
        
        stats = self.message_handler.get_stats()
        
        assert stats['total_messages_processed'] == 3
        assert stats['user_messages'] == 2
        assert stats['ai_messages'] == 1  # AI回复
        assert stats['system_messages'] == 1
        assert stats['ai_mentions_processed'] == 1
        assert 'ai_mention_rate' in stats
        assert 'rejection_rate' in stats
        assert 'ai_client_available' in stats
    
    def test_reset_stats(self):
        """测试重置统计信息"""
        # 先处理一些消息
        self.message_handler.process_message("测试消息", "测试用户", "session_123")
        
        # 检查有统计数据
        stats_before = self.message_handler.get_stats()
        assert stats_before['total_messages_processed'] > 0
        
        # 重置统计
        self.message_handler.reset_stats()
        
        # 检查统计已重置
        stats_after = self.message_handler.get_stats()
        assert stats_after['total_messages_processed'] == 0
        assert stats_after['user_messages'] == 0
        assert stats_after['ai_messages'] == 0


class TestMessageProcessor:
    """消息处理器高级封装测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 重置聊天室状态
        ChatRoomManager.get_instance().reset_chat_room()
        
        # 使用模拟AI客户端
        with patch('services.message_handler.get_ai_client') as mock_get_ai_client:
            mock_get_ai_client.return_value = MockAIClient()
            self.message_processor = MessageProcessor()
        
        # 添加测试用户
        self.message_processor.message_handler.user_manager.add_user("session_123", "测试用户", "socket_123")
    
    def test_process_user_message(self):
        """测试处理用户消息的便捷方法"""
        result = self.message_processor.process_user_message("你好", "测试用户", "session_123")
        
        assert result['success'] is True
        assert result['message'] is not None
        assert result['message'].message_type == "user"
    
    def test_process_system_notification(self):
        """测试处理系统通知的便捷方法"""
        result = self.message_processor.process_system_notification("系统维护通知")
        
        assert result['success'] is True
        assert result['message'] is not None
        assert result['message'].message_type == "system"
    
    def test_handle_user_join(self):
        """测试处理用户加入通知"""
        result = self.message_processor.handle_user_join("新用户")
        
        assert result['success'] is True
        assert result['message'] is not None
        assert "新用户" in result['message'].content
        assert "加入" in result['message'].content
    
    def test_handle_user_leave(self):
        """测试处理用户离开通知"""
        result = self.message_processor.handle_user_leave("离开用户")
        
        assert result['success'] is True
        assert result['message'] is not None
        assert "离开用户" in result['message'].content
        assert "离开" in result['message'].content
    
    def test_handle_ai_greeting(self):
        """测试处理AI问候"""
        result = self.message_processor.handle_ai_greeting("新用户")
        
        assert result['success'] is True
        assert result['message'] is not None
        assert result['message'].message_type == "ai"
        assert "新用户" in result['message'].content
        assert result['broadcast_data'] is not None
    
    def test_handle_ai_farewell(self):
        """测试处理AI告别"""
        result = self.message_processor.handle_ai_farewell("离开用户")
        
        assert result['success'] is True
        assert result['message'] is not None
        assert result['message'].message_type == "ai"
        assert "离开用户" in result['message'].content
        assert result['broadcast_data'] is not None
    
    def test_validate_message_before_processing(self):
        """测试处理前验证消息"""
        # 有效消息
        valid, message = self.message_processor.validate_message_before_processing("测试消息", "测试用户")
        assert valid is True
        assert "通过" in message
        
        # 无效消息
        valid, message = self.message_processor.validate_message_before_processing("", "测试用户")
        assert valid is False
        assert "不能为空" in message
        
        # 无效用户
        valid, message = self.message_processor.validate_message_before_processing("测试消息", "不存在的用户")
        assert valid is False
        assert "未在线" in message or "不存在" in message
    
    def test_get_processing_stats(self):
        """测试获取处理统计信息"""
        # 处理一些消息
        self.message_processor.process_user_message("消息1", "测试用户", "session_123")
        self.message_processor.process_system_notification("系统通知")
        
        stats = self.message_processor.get_processing_stats()
        
        assert 'total_messages_processed' in stats
        assert 'queue_size' in stats
        assert 'max_queue_size' in stats
        assert 'queue_usage' in stats
        assert stats['total_messages_processed'] >= 2
    
    def test_reset_all_stats(self):
        """测试重置所有统计信息"""
        # 处理一些消息
        self.message_processor.process_user_message("测试消息", "测试用户", "session_123")
        
        # 重置统计
        self.message_processor.reset_all_stats()
        
        # 检查统计已重置
        stats = self.message_processor.get_processing_stats()
        assert stats['total_messages_processed'] == 0
        assert stats['queue_size'] == 0


class TestMessageBatchProcessor:
    """批量消息处理器测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 重置聊天室状态
        ChatRoomManager.get_instance().reset_chat_room()
        
        # 使用模拟AI客户端
        with patch('services.message_handler.get_ai_client') as mock_get_ai_client:
            mock_get_ai_client.return_value = MockAIClient()
            message_handler = MessageHandler()
        
        # 添加测试用户
        message_handler.user_manager.add_user("session_123", "测试用户", "socket_123")
        
        self.batch_processor = MessageBatchProcessor(message_handler)
    
    def test_process_message_batch(self):
        """测试批量处理消息"""
        messages = [
            {
                'type': 'user',
                'content': '用户消息1',
                'username': '测试用户',
                'session_id': 'session_123'
            },
            {
                'type': 'system',
                'content': '系统通知1'
            },
            {
                'type': 'user',
                'content': '@AI 你好',
                'username': '测试用户',
                'session_id': 'session_123'
            }
        ]
        
        results = self.batch_processor.process_message_batch(messages)
        
        assert len(results) == 3
        assert all(result['success'] for result in results)
        assert results[0]['message'].message_type == 'user'
        assert results[1]['message'].message_type == 'system'
        assert results[2]['ai_response'] is not None  # 包含AI回复
    
    def test_process_message_batch_with_invalid_type(self):
        """测试批量处理包含无效类型的消息"""
        messages = [
            {
                'type': 'invalid',
                'content': '无效类型消息',
                'username': '测试用户'
            }
        ]
        
        results = self.batch_processor.process_message_batch(messages)
        
        assert len(results) == 1
        assert results[0]['success'] is False
        assert "未知消息类型" in results[0]['error']
    
    def test_validate_message_batch(self):
        """测试批量验证消息"""
        messages = [
            {
                'content': '有效消息',
                'username': '测试用户'
            },
            {
                'content': '',  # 无效：空内容
                'username': '测试用户'
            },
            {
                'content': '有效消息',
                'username': '不存在的用户'  # 无效：用户不存在
            }
        ]
        
        results = self.batch_processor.validate_message_batch(messages)
        
        assert len(results) == 3
        assert results[0]['valid'] is True
        assert results[1]['valid'] is False
        assert "不能为空" in results[1]['error']
        assert results[2]['valid'] is False
        assert "未在线" in results[2]['error'] or "不存在" in results[2]['error']


class TestMessageHandlerIntegration:
    """消息处理器集成测试"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 重置聊天室状态
        ChatRoomManager.get_instance().reset_chat_room()
        
        # 使用模拟AI客户端
        with patch('services.message_handler.get_ai_client') as mock_get_ai_client:
            mock_get_ai_client.return_value = MockAIClient()
            self.message_processor = MessageProcessor()
        
        # 添加测试用户
        self.message_processor.message_handler.user_manager.add_user("session_1", "张三", "socket_1")
        self.message_processor.message_handler.user_manager.add_user("session_2", "李四", "socket_2")
    
    def test_complete_chat_session_flow(self):
        """测试完整的聊天会话流程"""
        # 1. 用户加入通知
        join_result = self.message_processor.handle_user_join("王五")
        assert join_result['success'] is True
        assert "王五" in join_result['message'].content
        
        # 2. AI问候
        greeting_result = self.message_processor.handle_ai_greeting("王五")
        assert greeting_result['success'] is True
        assert greeting_result['message'].message_type == "ai"
        
        # 3. 用户聊天
        chat_result = self.message_processor.process_user_message("大家好！", "张三", "session_1")
        assert chat_result['success'] is True
        assert chat_result['message'].username == "张三"
        
        # 4. 用户@AI
        ai_mention_result = self.message_processor.process_user_message("@AI 你好", "李四", "session_2")
        assert ai_mention_result['success'] is True
        assert ai_mention_result['ai_response'] is not None
        assert ai_mention_result['ai_response'].message_type == "ai"
        
        # 5. 系统通知
        system_result = self.message_processor.process_system_notification("服务器将在5分钟后重启")
        assert system_result['success'] is True
        assert system_result['message'].message_type == "system"
        
        # 6. 用户离开通知
        leave_result = self.message_processor.handle_user_leave("张三")
        assert leave_result['success'] is True
        assert "张三" in leave_result['message'].content
        
        # 7. AI告别
        farewell_result = self.message_processor.handle_ai_farewell("张三")
        assert farewell_result['success'] is True
        assert farewell_result['message'].message_type == "ai"
        
        # 验证统计信息
        stats = self.message_processor.get_processing_stats()
        assert stats['total_messages_processed'] >= 7
        assert stats['user_messages'] >= 2
        assert stats['ai_messages'] >= 3  # 问候 + AI回复 + 告别
        assert stats['system_messages'] >= 3  # 加入 + 系统通知 + 离开
        assert stats['ai_mentions_processed'] >= 1
    
    def test_error_handling_flow(self):
        """测试错误处理流程"""
        # 1. 无效用户消息
        invalid_user_result = self.message_processor.process_user_message("测试消息", "不存在的用户")
        assert invalid_user_result['success'] is False
        assert "未在线" in invalid_user_result['error'] or "不存在" in invalid_user_result['error']
        
        # 2. 空消息内容
        empty_content_result = self.message_processor.process_user_message("", "张三", "session_1")
        assert empty_content_result['success'] is False
        assert "不能为空" in empty_content_result['error']
        
        # 3. 会话验证失败
        session_mismatch_result = self.message_processor.process_user_message("测试消息", "张三", "wrong_session")
        assert session_mismatch_result['success'] is False
        assert "验证失败" in session_mismatch_result['error']
        
        # 验证错误统计
        stats = self.message_processor.get_processing_stats()
        assert stats['invalid_messages_rejected'] >= 3
        assert stats['rejection_rate'] > 0
    
    def test_ai_interaction_flow(self):
        """测试AI交互流程"""
        # 1. 多次@AI交互
        ai_interactions = [
            "@AI 你好",
            "@AI 今天天气怎么样？",
            "@AI 谢谢你的帮助"
        ]
        
        ai_responses = []
        for interaction in ai_interactions:
            result = self.message_processor.process_user_message(interaction, "张三", "session_1")
            assert result['success'] is True
            assert result['ai_response'] is not None
            ai_responses.append(result['ai_response'])
        
        # 验证AI回复
        for response in ai_responses:
            assert response.message_type == "ai"
            assert response.username == "AI助手"
            assert len(response.content) > 0
        
        # 验证统计信息
        stats = self.message_processor.get_processing_stats()
        assert stats['ai_mentions_processed'] == 3
        assert stats['ai_messages'] == 3
        assert stats['ai_mention_rate'] > 0
    
    def test_concurrent_message_processing(self):
        """测试并发消息处理"""
        import threading
        import time
        
        results = []
        
        def process_messages(user_id, count):
            for i in range(count):
                try:
                    result = self.message_processor.process_user_message(
                        f"来自用户{user_id}的消息{i}",
                        "张三" if user_id % 2 == 0 else "李四",
                        "session_1" if user_id % 2 == 0 else "session_2"
                    )
                    results.append(result['success'])
                    time.sleep(0.001)  # 短暂延迟
                except Exception as e:
                    results.append(False)
                    print(f"处理消息失败: {e}")
        
        # 创建多个线程同时处理消息
        threads = []
        for i in range(3):
            t = threading.Thread(target=process_messages, args=(i, 5))
            threads.append(t)
        
        # 启动所有线程
        for t in threads:
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证结果
        assert len(results) == 15  # 3个线程 × 5条消息
        assert all(results)  # 所有消息都应该处理成功
        
        # 验证最终统计
        stats = self.message_processor.get_processing_stats()
        assert stats['total_messages_processed'] >= 15