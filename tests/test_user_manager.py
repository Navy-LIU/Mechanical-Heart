"""
用户管理组件单元测试
"""
import pytest
from datetime import datetime
import time

from services.user_manager import (
    UserManager, UserSessionManager, get_user_manager, UserEventHandler
)
from models.chat_room import ChatRoomManager
from models.user import create_user


class TestUserManager:
    """用户管理器测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 重置聊天室状态
        ChatRoomManager.get_instance().reset_chat_room()
        self.user_manager = UserManager()
    
    def test_add_user_success(self):
        """测试成功添加用户"""
        success, message, user = self.user_manager.add_user("session_123", "测试用户", "socket_123")
        
        assert success is True
        assert "欢迎" in message
        assert user is not None
        assert user.username == "测试用户"
        assert user.session_id == "session_123"
        
        # 检查用户是否在聊天室中
        assert self.user_manager.is_user_online_by_session("session_123")
        assert self.user_manager.is_user_online_by_username("测试用户")
        assert self.user_manager.is_user_online_by_socket("socket_123")
    
    def test_add_user_duplicate_username(self):
        """测试添加重复用户名"""
        # 添加第一个用户
        success1, _, _ = self.user_manager.add_user("session_1", "测试用户", "socket_1")
        assert success1 is True
        
        # 尝试添加相同用户名的用户
        success2, message2, user2 = self.user_manager.add_user("session_2", "测试用户", "socket_2")
        assert success2 is False
        assert "已被占用" in message2
        assert user2 is None
    
    def test_add_user_duplicate_session(self):
        """测试添加重复会话ID"""
        # 添加第一个用户
        success1, _, user1 = self.user_manager.add_user("session_123", "用户1", "socket_1")
        assert success1 is True
        
        # 尝试使用相同会话ID添加用户
        success2, message2, user2 = self.user_manager.add_user("session_123", "用户2", "socket_2")
        assert success2 is False
        assert "会话已存在" in message2
        assert user2 == user1  # 返回已存在的用户
    
    def test_add_user_invalid_username(self):
        """测试添加无效用户名"""
        invalid_usernames = ["", "123456", "user@name", "ai", "admin"]
        
        for username in invalid_usernames:
            success, message, user = self.user_manager.add_user(f"session_{username}", username)
            assert success is False
            assert user is None
            assert "格式无效" in message or "已被占用" in message
    
    def test_add_user_empty_parameters(self):
        """测试空参数"""
        # 空会话ID
        success, message, user = self.user_manager.add_user("", "用户名")
        assert success is False
        assert "不能为空" in message
        
        # 空用户名
        success, message, user = self.user_manager.add_user("session_123", "")
        assert success is False
        assert "不能为空" in message
    
    def test_remove_user_success(self):
        """测试成功移除用户"""
        # 先添加用户
        self.user_manager.add_user("session_123", "测试用户", "socket_123")
        
        # 移除用户
        success, message, user = self.user_manager.remove_user("session_123")
        
        assert success is True
        assert "已离开聊天室" in message
        assert user is not None
        assert user.username == "测试用户"
        
        # 检查用户是否已离开
        assert not self.user_manager.is_user_online_by_session("session_123")
        assert not self.user_manager.is_user_online_by_username("测试用户")
    
    def test_remove_nonexistent_user(self):
        """测试移除不存在的用户"""
        success, message, user = self.user_manager.remove_user("nonexistent_session")
        
        assert success is False
        assert "不存在" in message
        assert user is None
    
    def test_remove_ai_user(self):
        """测试不能移除AI用户"""
        ai_user = self.user_manager.chat_room.ai_user
        
        success, message, user = self.user_manager.remove_user(ai_user.session_id)
        
        assert success is False
        assert "不能移除AI用户" in message
        assert user is None
        
        # AI用户应该仍然在线
        assert self.user_manager.is_user_online_by_session(ai_user.session_id)
    
    def test_remove_user_by_socket(self):
        """测试根据Socket ID移除用户"""
        # 添加用户
        self.user_manager.add_user("session_123", "测试用户", "socket_123")
        
        # 根据Socket ID移除
        success, message, user = self.user_manager.remove_user_by_socket("socket_123")
        
        assert success is True
        assert user.username == "测试用户"
        assert not self.user_manager.is_user_online_by_socket("socket_123")
    
    def test_remove_user_by_nonexistent_socket(self):
        """测试根据不存在的Socket ID移除用户"""
        success, message, user = self.user_manager.remove_user_by_socket("nonexistent_socket")
        
        assert success is False
        assert "不存在" in message
        assert user is None
    
    def test_get_user_methods(self):
        """测试获取用户的各种方法"""
        # 添加用户
        self.user_manager.add_user("session_123", "测试用户", "socket_123")
        
        # 根据会话ID获取
        user1 = self.user_manager.get_user_by_session("session_123")
        assert user1 is not None
        assert user1.username == "测试用户"
        
        # 根据Socket ID获取
        user2 = self.user_manager.get_user_by_socket("socket_123")
        assert user2 is not None
        assert user2.username == "测试用户"
        assert user1 == user2
        
        # 根据用户名获取
        user3 = self.user_manager.get_user_by_username("测试用户")
        assert user3 is not None
        assert user3.username == "测试用户"
        assert user1 == user3
        
        # 不存在的情况
        assert self.user_manager.get_user_by_session("nonexistent") is None
        assert self.user_manager.get_user_by_socket("nonexistent") is None
        assert self.user_manager.get_user_by_username("不存在") is None
    
    def test_online_status_checks(self):
        """测试在线状态检查"""
        # 添加用户
        self.user_manager.add_user("session_123", "测试用户", "socket_123")
        
        # 检查在线状态
        assert self.user_manager.is_user_online_by_session("session_123")
        assert self.user_manager.is_user_online_by_username("测试用户")
        assert self.user_manager.is_user_online_by_socket("socket_123")
        
        # 检查不在线的情况
        assert not self.user_manager.is_user_online_by_session("nonexistent")
        assert not self.user_manager.is_user_online_by_username("不存在")
        assert not self.user_manager.is_user_online_by_socket("nonexistent")
        
        # 移除用户后检查
        self.user_manager.remove_user("session_123")
        assert not self.user_manager.is_user_online_by_session("session_123")
        assert not self.user_manager.is_user_online_by_username("测试用户")
        assert not self.user_manager.is_user_online_by_socket("socket_123")
    
    def test_socket_mapping_operations(self):
        """测试Socket映射操作"""
        # 添加用户
        self.user_manager.add_user("session_123", "测试用户", "socket_123")
        
        # 检查映射
        assert self.user_manager.get_session_by_socket("socket_123") == "session_123"
        assert self.user_manager.get_socket_by_session("session_123") == "socket_123"
        
        # 更新映射
        success = self.user_manager.update_socket_mapping("session_123", "new_socket_123")
        assert success is True
        assert self.user_manager.get_socket_by_session("session_123") == "new_socket_123"
        assert self.user_manager.get_session_by_socket("new_socket_123") == "session_123"
        
        # 旧Socket应该不再映射
        assert self.user_manager.get_session_by_socket("socket_123") is None
        
        # 清理映射
        success = self.user_manager.cleanup_socket_mapping("new_socket_123")
        assert success is True
        assert self.user_manager.get_session_by_socket("new_socket_123") is None
        assert self.user_manager.get_socket_by_session("session_123") is None
    
    def test_get_online_users_and_count(self):
        """测试获取在线用户列表和数量"""
        # 初始状态（只有AI用户）
        initial_count = self.user_manager.get_online_user_count()
        initial_users = self.user_manager.get_online_users()
        
        assert initial_count == 1  # 只有AI用户
        assert len(initial_users) == 1
        assert initial_users[0]['is_ai'] is True
        
        # 添加用户
        self.user_manager.add_user("session_1", "用户1", "socket_1")
        self.user_manager.add_user("session_2", "用户2", "socket_2")
        
        # 检查更新后的状态
        count = self.user_manager.get_online_user_count()
        users = self.user_manager.get_online_users()
        
        assert count == 3  # AI + 2个用户
        assert len(users) == 3
        
        # AI用户应该在第一位
        assert users[0]['is_ai'] is True
        
        # 检查用户信息格式
        for user_info in users:
            assert 'username' in user_info
            assert 'is_ai' in user_info
            assert 'join_time' in user_info
            assert 'session_id' not in user_info  # 不应该包含敏感信息
    
    def test_user_statistics(self):
        """测试用户统计"""
        # 添加用户
        self.user_manager.add_user("session_1", "用户1", "socket_1")
        self.user_manager.add_user("session_2", "用户2", "socket_2")
        
        stats = self.user_manager.get_user_statistics()
        
        assert stats['total_online_users'] == 3  # AI + 2用户
        assert stats['regular_users'] == 2
        assert stats['ai_users'] == 1
        assert stats['socket_connections'] == 2
        assert stats['session_mappings'] == 2
    
    def test_validate_user_session(self):
        """测试用户会话验证"""
        # 添加用户
        self.user_manager.add_user("session_123", "测试用户")
        
        # 正确的验证
        valid, message = self.user_manager.validate_user_session("session_123", "测试用户")
        assert valid is True
        assert "成功" in message
        
        # 错误的用户名
        valid, message = self.user_manager.validate_user_session("session_123", "错误用户名")
        assert valid is False
        assert "不匹配" in message
        
        # 不存在的会话
        valid, message = self.user_manager.validate_user_session("nonexistent", "测试用户")
        assert valid is False
        assert "不存在" in message
    
    def test_get_user_display_info(self):
        """测试获取用户显示信息"""
        # 添加用户
        self.user_manager.add_user("session_123", "测试用户")
        
        info = self.user_manager.get_user_display_info("session_123")
        
        assert info is not None
        assert info['username'] == "测试用户"
        assert info['display_name'] == "测试用户"
        assert info['is_ai'] is False
        assert 'join_time' in info
        assert 'online_duration' in info
        assert info['online_duration'] >= 0
        
        # 不存在的用户
        info = self.user_manager.get_user_display_info("nonexistent")
        assert info is None
    
    def test_broadcast_user_list_update(self):
        """测试广播用户列表更新"""
        # 添加用户
        self.user_manager.add_user("session_123", "测试用户")
        
        update_data = self.user_manager.broadcast_user_list_update()
        
        assert update_data['type'] == 'users_update'
        assert 'users' in update_data
        assert 'count' in update_data
        assert 'timestamp' in update_data
        assert update_data['count'] == 2  # AI + 1用户
        assert len(update_data['users']) == 2
    
    def test_user_limit(self):
        """测试用户数量限制"""
        # 设置较小的用户限制
        self.user_manager.chat_room.max_users = 3  # AI + 2个普通用户
        
        # 添加用户直到达到限制
        success1, _, _ = self.user_manager.add_user("session_1", "用户1")
        success2, _, _ = self.user_manager.add_user("session_2", "用户2")
        
        assert success1 is True
        assert success2 is True
        
        # 尝试添加第三个用户应该失败
        success3, message3, _ = self.user_manager.add_user("session_3", "用户3")
        assert success3 is False
        assert "已满" in message3


class TestUserSessionManager:
    """用户会话管理器测试类"""
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = UserSessionManager()
        manager2 = UserSessionManager()
        
        # 应该是同一个实例
        assert manager1 is manager2
        
        # 用户管理器也应该是同一个
        user_mgr1 = manager1.get_user_manager()
        user_mgr2 = manager2.get_user_manager()
        assert user_mgr1 is user_mgr2
    
    def test_get_user_manager_function(self):
        """测试便捷函数"""
        mgr1 = get_user_manager()
        mgr2 = get_user_manager()
        
        # 应该返回同一个用户管理器实例
        assert mgr1 is mgr2
        assert isinstance(mgr1, UserManager)


class TestUserEventHandler:
    """用户事件处理器测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        ChatRoomManager.get_instance().reset_chat_room()
        self.user_manager = UserManager()
        self.event_handler = UserEventHandler(self.user_manager)
    
    def test_handle_user_join_success(self):
        """测试处理用户加入成功"""
        result = self.event_handler.handle_user_join("session_123", "测试用户", "socket_123")
        
        assert result['success'] is True
        assert "欢迎" in result['message']
        assert result['user'] is not None
        assert result['user']['username'] == "测试用户"
        assert 'users_update' in result
        assert 'welcome_message' in result
        assert 'timestamp' in result
    
    def test_handle_user_join_failure(self):
        """测试处理用户加入失败"""
        # 先添加一个用户
        self.user_manager.add_user("session_1", "测试用户")
        
        # 尝试添加重复用户名
        result = self.event_handler.handle_user_join("session_2", "测试用户", "socket_2")
        
        assert result['success'] is False
        assert "已被占用" in result['message']
        assert result['user'] is None
        assert 'users_update' not in result
        assert 'welcome_message' not in result
    
    def test_handle_user_leave_success(self):
        """测试处理用户离开成功"""
        # 先添加用户
        self.user_manager.add_user("session_123", "测试用户", "socket_123")
        
        # 处理用户离开
        result = self.event_handler.handle_user_leave("session_123")
        
        assert result['success'] is True
        assert "离开了聊天室" in result['message']
        assert result['user'] is not None
        assert result['user']['username'] == "测试用户"
        assert 'users_update' in result
        assert 'goodbye_message' in result
        assert 'timestamp' in result
    
    def test_handle_user_leave_failure(self):
        """测试处理用户离开失败"""
        result = self.event_handler.handle_user_leave("nonexistent_session")
        
        assert result['success'] is False
        assert "不存在" in result['message']
        assert result['user'] is None
        assert 'users_update' not in result
        assert 'goodbye_message' not in result
    
    def test_handle_socket_disconnect(self):
        """测试处理Socket断开"""
        # 先添加用户
        self.user_manager.add_user("session_123", "测试用户", "socket_123")
        
        # 处理Socket断开
        result = self.event_handler.handle_socket_disconnect("socket_123")
        
        assert result['success'] is True
        assert result['user']['username'] == "测试用户"
        assert result['socket_id'] == "socket_123"
        assert 'users_update' in result
        assert 'disconnect_message' in result
        assert 'timestamp' in result
        
        # Socket映射应该被清理
        assert not self.user_manager.is_user_online_by_socket("socket_123")
    
    def test_handle_socket_disconnect_nonexistent(self):
        """测试处理不存在的Socket断开"""
        result = self.event_handler.handle_socket_disconnect("nonexistent_socket")
        
        assert result['success'] is False
        assert result['socket_id'] == "nonexistent_socket"
        assert 'users_update' not in result
        assert 'disconnect_message' not in result


class TestUserManagerIntegration:
    """用户管理器集成测试"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        ChatRoomManager.get_instance().reset_chat_room()
        self.user_manager = UserManager()
        self.event_handler = UserEventHandler(self.user_manager)
    
    def test_complete_user_lifecycle(self):
        """测试完整的用户生命周期"""
        # 1. 用户加入
        join_result = self.event_handler.handle_user_join("session_123", "张三", "socket_123")
        assert join_result['success'] is True
        assert self.user_manager.get_online_user_count() == 2  # AI + 1用户
        
        # 2. 验证用户状态
        assert self.user_manager.is_user_online_by_session("session_123")
        assert self.user_manager.is_user_online_by_username("张三")
        assert self.user_manager.is_user_online_by_socket("socket_123")
        
        # 3. 获取用户信息
        user = self.user_manager.get_user_by_session("session_123")
        assert user.username == "张三"
        
        display_info = self.user_manager.get_user_display_info("session_123")
        assert display_info['username'] == "张三"
        
        # 4. 更新Socket映射
        success = self.user_manager.update_socket_mapping("session_123", "new_socket_123")
        assert success is True
        assert self.user_manager.get_socket_by_session("session_123") == "new_socket_123"
        
        # 5. 用户离开
        leave_result = self.event_handler.handle_user_leave("session_123")
        assert leave_result['success'] is True
        assert self.user_manager.get_online_user_count() == 1  # 只剩AI用户
        
        # 6. 验证用户已离开
        assert not self.user_manager.is_user_online_by_session("session_123")
        assert not self.user_manager.is_user_online_by_username("张三")
    
    def test_multiple_users_management(self):
        """测试多用户管理"""
        users = [
            ("session_1", "张三", "socket_1"),
            ("session_2", "李四", "socket_2"),
            ("session_3", "王五", "socket_3")
        ]
        
        # 添加多个用户
        for session_id, username, socket_id in users:
            result = self.event_handler.handle_user_join(session_id, username, socket_id)
            assert result['success'] is True
        
        # 验证用户数量
        assert self.user_manager.get_online_user_count() == 4  # AI + 3用户
        
        # 验证用户列表
        online_users = self.user_manager.get_online_users()
        assert len(online_users) == 4
        
        # AI用户应该在第一位
        assert online_users[0]['is_ai'] is True
        
        # 验证统计信息
        stats = self.user_manager.get_user_statistics()
        assert stats['regular_users'] == 3
        assert stats['socket_connections'] == 3
        
        # 移除一个用户
        leave_result = self.event_handler.handle_user_leave("session_2")
        assert leave_result['success'] is True
        assert self.user_manager.get_online_user_count() == 3
        
        # 验证剩余用户
        assert self.user_manager.is_user_online_by_username("张三")
        assert not self.user_manager.is_user_online_by_username("李四")
        assert self.user_manager.is_user_online_by_username("王五")
    
    def test_socket_disconnect_scenarios(self):
        """测试Socket断开场景"""
        # 添加用户
        self.user_manager.add_user("session_123", "测试用户", "socket_123")
        
        # 模拟Socket断开
        disconnect_result = self.event_handler.handle_socket_disconnect("socket_123")
        assert disconnect_result['success'] is True
        
        # 用户应该被移除
        assert not self.user_manager.is_user_online_by_session("session_123")
        
        # Socket映射应该被清理
        mappings = self.user_manager.get_all_socket_mappings()
        assert "socket_123" not in mappings['socket_to_session']
        assert "session_123" not in mappings['session_to_socket']
    
    def test_error_handling_and_edge_cases(self):
        """测试错误处理和边界情况"""
        # 空参数处理
        result = self.event_handler.handle_user_join("", "")
        assert result['success'] is False
        
        # 无效用户名处理
        result = self.event_handler.handle_user_join("session_123", "123456")
        assert result['success'] is False
        
        # 移除不存在的用户
        result = self.event_handler.handle_user_leave("nonexistent")
        assert result['success'] is False
        
        # 断开不存在的Socket
        result = self.event_handler.handle_socket_disconnect("nonexistent")
        assert result['success'] is False
        
        # 尝试移除AI用户
        ai_session = self.user_manager.chat_room.ai_user.session_id
        result = self.event_handler.handle_user_leave(ai_session)
        assert result['success'] is False