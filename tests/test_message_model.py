"""
消息模型单元测试
"""
import pytest
from datetime import datetime
from models.message import (
    Message, create_user_message, create_ai_message, create_system_message,
    MessageValidator, MessageFormatter
)


class TestMessage:
    """消息模型测试类"""
    
    def test_create_valid_message(self):
        """测试创建有效消息"""
        timestamp = datetime.now()
        message = Message(
            id="msg_123",
            content="这是一条测试消息",
            username="测试用户",
            timestamp=timestamp,
            message_type="user"
        )
        
        assert message.id == "msg_123"
        assert message.content == "这是一条测试消息"
        assert message.username == "测试用户"
        assert message.timestamp == timestamp
        assert message.message_type == "user"
        assert message.mentions_ai is False
    
    def test_create_message_with_factory_functions(self):
        """测试使用工厂函数创建消息"""
        # 用户消息
        user_msg = create_user_message("用户1", "Hello World")
        assert user_msg.username == "用户1"
        assert user_msg.content == "Hello World"
        assert user_msg.message_type == "user"
        assert isinstance(user_msg.timestamp, datetime)
        
        # AI消息
        ai_msg = create_ai_message("AI助手", "你好！")
        assert ai_msg.username == "AI助手"
        assert ai_msg.content == "你好！"
        assert ai_msg.message_type == "ai"
        
        # 系统消息
        sys_msg = create_system_message("用户已加入聊天室")
        assert sys_msg.username == "系统"
        assert sys_msg.content == "用户已加入聊天室"
        assert sys_msg.message_type == "system"
    
    def test_message_validation_empty_fields(self):
        """测试空字段验证"""
        timestamp = datetime.now()
        
        # 空ID
        with pytest.raises(ValueError, match="消息ID不能为空"):
            Message("", "内容", "用户", timestamp, "user")
        
        # 空内容
        with pytest.raises(ValueError, match="消息内容不能为空"):
            Message("msg_123", "", "用户", timestamp, "user")
        
        # 空用户名
        with pytest.raises(ValueError, match="用户名不能为空"):
            Message("msg_123", "内容", "", timestamp, "user")
    
    def test_message_validation_invalid_type(self):
        """测试无效消息类型验证"""
        with pytest.raises(ValueError, match="message_type必须是"):
            Message("msg_123", "内容", "用户", datetime.now(), "invalid_type")
    
    def test_message_validation_content_length(self):
        """测试消息内容长度验证"""
        long_content = "a" * 1001  # 超过1000字符
        with pytest.raises(ValueError, match="消息内容不能超过1000个字符"):
            Message("msg_123", long_content, "用户", datetime.now(), "user")
    
    def test_message_validation_username_length(self):
        """测试用户名长度验证"""
        long_username = "a" * 21  # 超过20字符
        with pytest.raises(ValueError, match="用户名长度不能超过20个字符"):
            Message("msg_123", "内容", long_username, datetime.now(), "user")
    
    def test_ai_mention_detection(self):
        """测试@AI提及检测"""
        test_cases = [
            ("@AI 你好", True),
            ("@ai 帮我解答", True),
            ("@Ai 问题", True),
            ("@AI助手 请帮忙", True),
            ("@ai助手 谢谢", True),
            ("@智能助手 你好", True),
            ("@助手 帮忙", True),
            ("普通消息", False),
            ("这里没有提及", False),
            ("email@domain.com", False),  # 不应该匹配邮箱
            ("AI很厉害", False),  # 不应该匹配没有@的AI
        ]
        
        for content, expected in test_cases:
            message = create_user_message("用户", content)
            assert message.mentions_ai == expected, f"内容 '{content}' 的检测结果应该是 {expected}"
    
    def test_ai_mention_content_extraction(self):
        """测试@AI内容提取"""
        test_cases = [
            ("@AI 你好吗？", "你好吗？"),
            ("@ai    帮我解答这个问题", "帮我解答这个问题"),
            ("@AI助手 请告诉我时间", "请告诉我时间"),
            ("普通消息", ""),  # 没有@AI的消息应该返回空字符串
        ]
        
        for content, expected in test_cases:
            message = create_user_message("用户", content)
            extracted = message.extract_ai_mention_content()
            assert extracted == expected, f"从 '{content}' 提取的内容应该是 '{expected}'"
    
    def test_message_to_dict(self):
        """测试转换为字典"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        message = Message("msg_123", "测试内容", "用户", timestamp, "user")
        
        result = message.to_dict()
        expected = {
            'id': 'msg_123',
            'content': '测试内容',
            'username': '用户',
            'timestamp': '2024-01-01T12:00:00',
            'message_type': 'user',
            'mentions_ai': False
        }
        
        assert result == expected
    
    def test_message_format_for_display(self):
        """测试格式化为显示格式"""
        timestamp = datetime(2024, 1, 1, 12, 30, 45)
        message = Message("msg_123", "测试内容", "用户", timestamp, "user")
        
        result = message.format_for_display()
        
        assert result['id'] == 'msg_123'
        assert result['content'] == '测试内容'
        assert result['username'] == '用户'
        assert result['message_type'] == 'user'
        assert result['formatted_time'] == '12:30:45'
        assert result['display_username'] == '用户'
    
    def test_ai_message_display_username(self):
        """测试AI消息的显示用户名"""
        ai_message = create_ai_message("AI助手", "你好")
        display_name = ai_message.get_display_username()
        assert display_name == "AI助手 (AI)"
    
    def test_system_message_display_username(self):
        """测试系统消息的显示用户名"""
        sys_message = create_system_message("用户已加入")
        display_name = sys_message.get_display_username()
        assert display_name == "系统"
    
    def test_message_type_checks(self):
        """测试消息类型检查方法"""
        user_msg = create_user_message("用户", "内容")
        ai_msg = create_ai_message("AI", "回复")
        sys_msg = create_system_message("通知")
        
        assert not user_msg.is_from_ai()
        assert not user_msg.is_system_message()
        
        assert ai_msg.is_from_ai()
        assert not ai_msg.is_system_message()
        
        assert not sys_msg.is_from_ai()
        assert sys_msg.is_system_message()
    
    def test_content_preview(self):
        """测试内容预览"""
        short_msg = create_user_message("用户", "短消息")
        long_msg = create_user_message("用户", "这是一条很长的消息" * 10)
        
        assert short_msg.get_content_preview() == "短消息"
        
        preview = long_msg.get_content_preview(20)
        assert len(preview) <= 23  # 20 + "..."
        assert preview.endswith("...")
    
    def test_message_equality(self):
        """测试消息相等性"""
        msg1 = Message("msg_123", "内容", "用户", datetime.now(), "user")
        msg2 = Message("msg_123", "不同内容", "不同用户", datetime.now(), "ai")  # 相同ID
        msg3 = Message("msg_456", "内容", "用户", datetime.now(), "user")  # 不同ID
        
        assert msg1 == msg2  # 相同ID应该相等
        assert msg1 != msg3  # 不同ID应该不相等
        assert msg1 != "not_a_message"  # 与非Message对象不相等
    
    def test_message_hash(self):
        """测试消息哈希值"""
        msg1 = Message("msg_123", "内容1", "用户1", datetime.now(), "user")
        msg2 = Message("msg_123", "内容2", "用户2", datetime.now(), "ai")
        msg3 = Message("msg_456", "内容1", "用户1", datetime.now(), "user")
        
        assert hash(msg1) == hash(msg2)  # 相同ID应该有相同哈希值
        assert hash(msg1) != hash(msg3)  # 不同ID应该有不同哈希值
    
    def test_html_escaping(self):
        """测试HTML转义"""
        malicious_content = "<script>alert('xss')</script>"
        message = create_user_message("用户", malicious_content)
        
        # 内容应该被HTML转义
        assert "<script>" not in message.content
        assert "&lt;script&gt;" in message.content


class TestMessageValidator:
    """消息验证器测试类"""
    
    def test_valid_content(self):
        """测试有效内容验证"""
        valid_contents = [
            "普通消息",
            "包含数字123",
            "包含符号！@#￥%",
            "中英文混合 Mixed Content",
            "@AI 你好",
        ]
        
        for content in valid_contents:
            assert MessageValidator.is_valid_content(content), f"内容 '{content}' 应该是有效的"
    
    def test_invalid_content(self):
        """测试无效内容验证"""
        invalid_contents = [
            "",  # 空字符串
            "   ",  # 只有空白
            "a" * 1001,  # 超长
            "<script>alert('xss')</script>",  # 恶意脚本
            "javascript:alert('xss')",  # JavaScript协议
            "<iframe src='evil.com'></iframe>",  # iframe标签
            None,  # None值
            123,  # 非字符串
        ]
        
        for content in invalid_contents:
            assert not MessageValidator.is_valid_content(content), f"内容 '{content}' 应该是无效的"
    
    def test_sanitize_content(self):
        """测试内容清理"""
        test_cases = [
            ("  普通消息  ", "普通消息"),
            ("<script>alert('xss')</script>", "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"),
            ("a" * 1001, "a" * 1000),  # 截断超长内容
            ("", ""),
        ]
        
        for input_content, expected in test_cases:
            result = MessageValidator.sanitize_content(input_content)
            assert result == expected, f"清理 '{input_content}' 应该得到 '{expected}'"
    
    def test_extract_mentions(self):
        """测试提取@提及"""
        test_cases = [
            ("@用户1 你好", ["用户1"]),
            ("@user1 @user2 大家好", ["user1", "user2"]),
            ("@AI @助手 请帮忙", ["AI", "助手"]),
            ("普通消息", []),
            ("email@domain.com", []),  # 不应该匹配邮箱
            ("@用户1 @用户1 重复", ["用户1"]),  # 应该去重
        ]
        
        for content, expected in test_cases:
            result = MessageValidator.extract_mentions(content)
            assert set(result) == set(expected), f"从 '{content}' 提取的@提及应该是 {expected}"


class TestMessageFormatter:
    """消息格式化器测试类"""
    
    def test_format_for_websocket(self):
        """测试WebSocket格式化"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        message = Message("msg_123", "测试内容", "用户", timestamp, "user")
        
        result = MessageFormatter.format_for_websocket(message)
        expected = {
            'id': 'msg_123',
            'content': '测试内容',
            'username': '用户',
            'timestamp': '2024-01-01T12:00:00',
            'message_type': 'user',
            'mentions_ai': False
        }
        
        assert result == expected
    
    def test_format_for_api(self):
        """测试API格式化"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        message = Message("msg_123", "测试内容", "用户", timestamp, "user")
        
        result = MessageFormatter.format_for_api(message)
        expected = {
            'message_id': 'msg_123',
            'text': '测试内容',
            'sender': '用户',
            'sent_at': '2024-01-01T12:00:00',
            'type': 'user',
            'ai_mentioned': False
        }
        
        assert result == expected
    
    def test_format_message_list(self):
        """测试消息列表格式化"""
        messages = [
            create_user_message("用户1", "消息1"),
            create_ai_message("AI", "回复1"),
            create_system_message("系统通知")
        ]
        
        result = MessageFormatter.format_message_list(messages)
        
        assert len(result) == 3
        assert all('id' in msg for msg in result)
        assert all('content' in msg for msg in result)
        assert all('display_username' in msg for msg in result)
        assert all('formatted_time' in msg for msg in result)


class TestMessageIntegration:
    """消息模型集成测试"""
    
    def test_complete_message_workflow(self):
        """测试完整的消息处理流程"""
        # 1. 创建用户消息
        user_msg = create_user_message("张三", "@AI 今天天气怎么样？")
        
        # 2. 验证消息属性
        assert user_msg.mentions_ai is True
        assert user_msg.message_type == "user"
        assert user_msg.username == "张三"
        
        # 3. 提取AI输入内容
        ai_input = user_msg.extract_ai_mention_content()
        assert ai_input == "今天天气怎么样？"
        
        # 4. 创建AI回复
        ai_msg = create_ai_message("AI助手", "今天天气晴朗，温度适宜。")
        
        # 5. 验证AI消息
        assert ai_msg.is_from_ai() is True
        assert ai_msg.mentions_ai is False  # AI消息不会检测@AI
        
        # 6. 格式化为显示格式
        user_display = user_msg.format_for_display()
        ai_display = ai_msg.format_for_display()
        
        assert user_display['display_username'] == "张三"
        assert ai_display['display_username'] == "AI助手 (AI)"
        
        # 7. 创建系统通知
        sys_msg = create_system_message("AI助手已回复")
        assert sys_msg.is_system_message() is True
    
    def test_message_security(self):
        """测试消息安全性"""
        # 测试XSS防护
        malicious_content = "<script>alert('xss')</script>onclick='evil()'"
        message = create_user_message("恶意用户", malicious_content)
        
        # 内容应该被转义
        assert "<script>" not in message.content
        assert "onclick=" not in message.content
        
        # 验证内容有效性
        assert MessageValidator.is_valid_content("正常内容")
        assert not MessageValidator.is_valid_content(malicious_content)
        
        # 内容清理
        cleaned = MessageValidator.sanitize_content(malicious_content)
        assert "<script>" not in cleaned
        assert "onclick=" not in cleaned