"""
用户模型单元测试
"""
import pytest
from datetime import datetime
from models.user import User, AIUser, create_user, create_ai_user


class TestUser:
    """用户模型测试类"""
    
    def test_create_valid_user(self):
        """测试创建有效用户"""
        user = User(
            session_id="test_session_123",
            username="测试用户",
            join_time=datetime.now()
        )
        
        assert user.session_id == "test_session_123"
        assert user.username == "测试用户"
        assert user.is_ai is False
        assert isinstance(user.join_time, datetime)
    
    def test_create_user_with_factory(self):
        """测试使用工厂函数创建用户"""
        user = create_user("session_456", "用户名")
        
        assert user.session_id == "session_456"
        assert user.username == "用户名"
        assert user.is_ai is False
        assert isinstance(user.join_time, datetime)
    
    def test_user_validation_empty_session_id(self):
        """测试空session_id验证"""
        with pytest.raises(ValueError, match="session_id不能为空"):
            User("", "用户名", datetime.now())
    
    def test_user_validation_empty_username(self):
        """测试空用户名验证"""
        with pytest.raises(ValueError, match="用户名不能为空"):
            User("session_123", "", datetime.now())
    
    def test_user_validation_invalid_join_time(self):
        """测试无效join_time验证"""
        with pytest.raises(ValueError, match="join_time必须是datetime对象"):
            User("session_123", "用户名", "invalid_time")
    
    def test_username_validation_valid_names(self):
        """测试有效用户名"""
        valid_names = [
            "用户123",
            "TestUser",
            "test_user",
            "用户_123",
            "张三",
            "John_Doe"
        ]
        
        for name in valid_names:
            assert User.is_valid_username(name), f"用户名 '{name}' 应该是有效的"
    
    def test_username_validation_invalid_names(self):
        """测试无效用户名"""
        invalid_names = [
            "",  # 空字符串
            "a" * 21,  # 超长
            "123456",  # 纯数字
            "user@name",  # 包含特殊字符
            "user name",  # 包含空格
            "ai",  # 保留关键词
            "AI",  # 保留关键词
            "admin",  # 保留关键词
            "system",  # 保留关键词
            None,  # None值
            123,  # 非字符串
        ]
        
        for name in invalid_names:
            assert not User.is_valid_username(name), f"用户名 '{name}' 应该是无效的"
    
    def test_user_to_dict(self):
        """测试转换为字典"""
        join_time = datetime(2024, 1, 1, 12, 0, 0)
        user = User("session_123", "测试用户", join_time)
        
        result = user.to_dict()
        expected = {
            'session_id': 'session_123',
            'username': '测试用户',
            'join_time': '2024-01-01T12:00:00',
            'is_ai': False
        }
        
        assert result == expected
    
    def test_user_to_public_dict(self):
        """测试转换为公开字典"""
        join_time = datetime(2024, 1, 1, 12, 0, 0)
        user = User("session_123", "测试用户", join_time)
        
        result = user.to_public_dict()
        expected = {
            'username': '测试用户',
            'is_ai': False,
            'join_time': '2024-01-01T12:00:00'
        }
        
        assert result == expected
        assert 'session_id' not in result  # 确保敏感信息不包含
    
    def test_user_is_online(self):
        """测试用户在线状态"""
        user = User("session_123", "测试用户", datetime.now())
        assert user.is_online() is True
        
        # 测试空session_id的情况
        user.session_id = ""
        assert user.is_online() is False
    
    def test_user_get_display_name(self):
        """测试获取显示名称"""
        user = User("session_123", "测试用户", datetime.now())
        assert user.get_display_name() == "测试用户"
        
        ai_user = User("session_ai", "AI助手", datetime.now(), is_ai=True)
        assert ai_user.get_display_name() == "AI助手 (AI)"
    
    def test_user_equality(self):
        """测试用户相等性比较"""
        user1 = User("session_123", "用户1", datetime.now())
        user2 = User("session_123", "用户2", datetime.now())  # 相同session_id
        user3 = User("session_456", "用户1", datetime.now())  # 不同session_id
        
        assert user1 == user2  # 相同session_id应该相等
        assert user1 != user3  # 不同session_id应该不相等
        assert user1 != "not_a_user"  # 与非User对象不相等
    
    def test_user_hash(self):
        """测试用户哈希值"""
        user1 = User("session_123", "用户1", datetime.now())
        user2 = User("session_123", "用户2", datetime.now())
        user3 = User("session_456", "用户1", datetime.now())
        
        assert hash(user1) == hash(user2)  # 相同session_id应该有相同哈希值
        assert hash(user1) != hash(user3)  # 不同session_id应该有不同哈希值
    
    def test_user_string_representation(self):
        """测试用户字符串表示"""
        user = User("session_123", "测试用户", datetime.now())
        
        str_repr = str(user)
        assert "测试用户" in str_repr
        assert "is_ai=False" in str_repr
        
        repr_str = repr(user)
        assert "session_123" in repr_str
        assert "测试用户" in repr_str


class TestAIUser:
    """AI用户测试类"""
    
    def test_create_ai_user(self):
        """测试创建AI用户"""
        ai_user = AIUser()
        
        assert ai_user.session_id == "ai_user_session"
        assert ai_user.username == "AI助手"
        assert ai_user.is_ai is True
        assert isinstance(ai_user.join_time, datetime)
    
    def test_create_ai_user_with_custom_name(self):
        """测试创建自定义名称的AI用户"""
        ai_user = AIUser("智能助手")
        
        assert ai_user.username == "智能助手"
        assert ai_user.is_ai is True
    
    def test_create_ai_user_with_factory(self):
        """测试使用工厂函数创建AI用户"""
        ai_user = create_ai_user("ChatBot")
        
        assert ai_user.username == "ChatBot"
        assert ai_user.is_ai is True
        assert ai_user.session_id == "ai_user_session"
    
    def test_ai_user_always_online(self):
        """测试AI用户始终在线"""
        ai_user = AIUser()
        assert ai_user.is_online() is True
        
        # 即使修改session_id，AI用户也应该在线
        ai_user.session_id = ""
        assert ai_user.is_online() is True
    
    def test_ai_user_validation_allows_reserved_names(self):
        """测试AI用户允许使用保留关键词"""
        # AI用户应该可以使用保留关键词作为用户名
        ai_user = AIUser("AI")
        assert ai_user.username == "AI"
        assert ai_user.is_ai is True
    
    def test_ai_user_validation_username_length(self):
        """测试AI用户名长度验证"""
        # 正常长度应该通过
        ai_user = AIUser("AI助手")
        assert ai_user.username == "AI助手"
        
        # 超长用户名应该失败
        with pytest.raises(ValueError, match="用户名长度不能超过20个字符"):
            AIUser("a" * 21)
    
    def test_ai_user_get_display_name(self):
        """测试AI用户显示名称"""
        ai_user = AIUser("智能助手")
        assert ai_user.get_display_name() == "智能助手 (AI)"


class TestUserValidation:
    """用户验证功能测试"""
    
    def test_invalid_user_creation_should_raise_exception(self):
        """测试创建无效用户应该抛出异常"""
        # 测试各种无效情况
        invalid_cases = [
            ("", "用户名", datetime.now()),  # 空session_id
            ("session_123", "", datetime.now()),  # 空用户名
            ("session_123", "123456", datetime.now()),  # 纯数字用户名
            ("session_123", "user@name", datetime.now()),  # 包含特殊字符
            ("session_123", "ai", datetime.now()),  # 保留关键词
        ]
        
        for session_id, username, join_time in invalid_cases:
            with pytest.raises(ValueError):
                User(session_id, username, join_time)
    
    def test_user_creation_with_valid_data(self):
        """测试使用有效数据创建用户"""
        valid_cases = [
            ("session_123", "用户123", datetime.now()),
            ("session_456", "TestUser", datetime.now()),
            ("session_789", "test_user", datetime.now()),
            ("session_abc", "张三", datetime.now()),
        ]
        
        for session_id, username, join_time in valid_cases:
            user = User(session_id, username, join_time)
            assert user.session_id == session_id
            assert user.username == username
            assert user.join_time == join_time