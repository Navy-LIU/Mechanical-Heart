"""
聊天室状态模型单元测试
"""
import pytest
from datetime import datetime
import threading
import time

from models.chat_room import (
    ChatRoomState, ChatRoomManager, get_chat_room, ChatRoomValidator
)
from models.user import create_user, create_ai_user
from models.message import create_user_message, create_ai_message, create_system_message


class TestChatRoomState:
    """聊天室状态测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.chat_room = ChatRoomState()
    
    def test_initial_state(self):
        """测试初始状态"""
        # 应该有AI用户在线
        assert len(self.chat_room.online_users) == 1
        assert self.chat_room.ai_user.session_id in self.chat_room.online_users
        
        # 应该有欢迎消息
        assert len(self.chat_room.message_history) == 1
        
        # 检查统计信息
        stats = self.chat_room.get_chat_statistics()
        assert stats['online_users'] == 1
        assert stats['total_messages'] == 1
    
    def test_add_user(self):
        """测试添加用户"""
        user = create_user("session_123", "测试用户")
        
        # 添加用户应该成功
        result = self.chat_room.add_user(user)
        assert result is True
        
        # 用户应该在在线列表中
        assert user.session_id in self.chat_room.online_users
        assert self.chat_room.get_online_user_count() == 2
        
        # 应该有加入通知消息
        messages = self.chat_room.get_recent_messages()
        join_messages = [msg for msg in messages if "加入了聊天室" in msg.content]
        assert len(join_messages) == 1
    
    def test_add_duplicate_username(self):
        """测试添加重复用户名"""
        user1 = create_user("session_123", "测试用户")
        user2 = create_user("session_456", "测试用户")  # 相同用户名
        
        # 第一个用户应该成功
        assert self.chat_room.add_user(user1) is True
        
        # 第二个用户应该失败（用户名重复）
        assert self.chat_room.add_user(user2) is False
        
        # 只应该有一个用户（除了AI）
        assert self.chat_room.get_online_user_count() == 2  # AI + 1个用户
    
    def test_user_limit(self):
        """测试用户数量限制"""
        # 设置较小的用户限制
        self.chat_room.max_users = 3  # AI + 2个普通用户
        
        user1 = create_user("session_1", "用户1")
        user2 = create_user("session_2", "用户2")
        user3 = create_user("session_3", "用户3")
        
        # 前两个用户应该成功
        assert self.chat_room.add_user(user1) is True
        assert self.chat_room.add_user(user2) is True
        
        # 第三个用户应该失败（超过限制）
        assert self.chat_room.add_user(user3) is False
        
        assert self.chat_room.get_online_user_count() == 3
    
    def test_remove_user(self):
        """测试移除用户"""
        user = create_user("session_123", "测试用户")
        self.chat_room.add_user(user)
        
        # 移除用户
        removed_user = self.chat_room.remove_user("session_123")
        assert removed_user == user
        
        # 用户应该不在在线列表中
        assert "session_123" not in self.chat_room.online_users
        assert self.chat_room.get_online_user_count() == 1  # 只剩AI
        
        # 应该有离开通知消息
        messages = self.chat_room.get_recent_messages()
        leave_messages = [msg for msg in messages if "离开了聊天室" in msg.content]
        assert len(leave_messages) == 1
    
    def test_cannot_remove_ai_user(self):
        """测试不能移除AI用户"""
        ai_session_id = self.chat_room.ai_user.session_id
        
        # 尝试移除AI用户应该失败
        result = self.chat_room.remove_user(ai_session_id)
        assert result is None
        
        # AI用户应该仍然在线
        assert ai_session_id in self.chat_room.online_users
    
    def test_get_user_methods(self):
        """测试获取用户的方法"""
        user = create_user("session_123", "测试用户")
        self.chat_room.add_user(user)
        
        # 根据session_id获取
        found_user = self.chat_room.get_user_by_session("session_123")
        assert found_user == user
        
        # 根据用户名获取
        found_user = self.chat_room.get_user_by_username("测试用户")
        assert found_user == user
        
        # 不存在的用户
        assert self.chat_room.get_user_by_session("nonexistent") is None
        assert self.chat_room.get_user_by_username("不存在") is None
    
    def test_username_taken_check(self):
        """测试用户名占用检查"""
        user = create_user("session_123", "测试用户")
        
        # 添加前不应该被占用
        assert not self.chat_room.is_username_taken("测试用户")
        
        # 添加用户
        self.chat_room.add_user(user)
        
        # 添加后应该被占用
        assert self.chat_room.is_username_taken("测试用户")
        
        # AI用户名也应该被占用
        assert self.chat_room.is_username_taken(self.chat_room.ai_user.username)
    
    def test_get_online_users(self):
        """测试获取在线用户列表"""
        user1 = create_user("session_1", "用户1")
        user2 = create_user("session_2", "用户2")
        
        self.chat_room.add_user(user1)
        self.chat_room.add_user(user2)
        
        users = self.chat_room.get_online_users()
        
        # 应该有3个用户（AI + 2个普通用户）
        assert len(users) == 3
        
        # AI用户应该在第一位
        assert users[0]['is_ai'] is True
        
        # 检查用户信息格式
        for user_info in users:
            assert 'username' in user_info
            assert 'is_ai' in user_info
            assert 'join_time' in user_info
            assert 'session_id' not in user_info  # 不应该包含敏感信息
    
    def test_message_operations(self):
        """测试消息操作"""
        # 添加消息
        msg1 = create_user_message("用户1", "消息1")
        msg2 = create_ai_message("AI", "回复1")
        
        self.chat_room.add_message(msg1)
        self.chat_room.add_message(msg2)
        
        # 获取最近消息
        recent = self.chat_room.get_recent_messages(10)
        assert len(recent) >= 3  # 欢迎消息 + 2条新消息
        
        # 检查消息顺序（最新的在后面）
        assert recent[-2] == msg1
        assert recent[-1] == msg2
    
    def test_get_messages_by_user(self):
        """测试按用户获取消息"""
        user = create_user("session_123", "测试用户")
        self.chat_room.add_user(user)
        
        # 添加多条消息
        msg1 = create_user_message("测试用户", "消息1")
        msg2 = create_user_message("其他用户", "消息2")
        msg3 = create_user_message("测试用户", "消息3")
        
        self.chat_room.add_message(msg1)
        self.chat_room.add_message(msg2)
        self.chat_room.add_message(msg3)
        
        # 获取指定用户的消息
        user_messages = self.chat_room.get_messages_by_user("测试用户")
        assert len(user_messages) == 2
        assert msg1 in user_messages
        assert msg3 in user_messages
        assert msg2 not in user_messages
    
    def test_get_ai_mentioned_messages(self):
        """测试获取提及AI的消息"""
        msg1 = create_user_message("用户1", "@AI 你好")
        msg2 = create_user_message("用户2", "普通消息")
        msg3 = create_user_message("用户3", "@AI 帮忙")
        
        self.chat_room.add_message(msg1)
        self.chat_room.add_message(msg2)
        self.chat_room.add_message(msg3)
        
        ai_messages = self.chat_room.get_ai_mentioned_messages()
        assert len(ai_messages) == 2
        assert msg1 in ai_messages
        assert msg3 in ai_messages
        assert msg2 not in ai_messages
    
    def test_clear_message_history(self):
        """测试清空消息历史"""
        # 添加一些消息
        msg1 = create_user_message("用户1", "消息1")
        msg2 = create_user_message("用户2", "消息2")
        
        self.chat_room.add_message(msg1)
        self.chat_room.add_message(msg2)
        
        original_count = len(self.chat_room.message_history)
        assert original_count > 1
        
        # 清空历史
        self.chat_room.clear_message_history()
        
        # 应该只剩下清空通知消息
        assert len(self.chat_room.message_history) == 1
        assert "消息历史已清空" in list(self.chat_room.message_history)[0].content
    
    def test_chat_statistics(self):
        """测试聊天统计"""
        user = create_user("session_123", "测试用户")
        self.chat_room.add_user(user)
        
        # 添加各种类型的消息
        user_msg = create_user_message("测试用户", "@AI 你好")
        ai_msg = create_ai_message("AI", "你好")
        sys_msg = create_system_message("系统通知")
        
        self.chat_room.add_message(user_msg)
        self.chat_room.add_message(ai_msg)
        self.chat_room.add_message(sys_msg)
        
        stats = self.chat_room.get_chat_statistics()
        
        assert stats['online_users'] == 2  # AI + 1个用户
        assert stats['user_messages'] == 1
        assert stats['ai_messages'] == 1
        assert stats['system_messages'] >= 2  # 加入通知 + 新系统消息
        assert stats['ai_mentions'] == 1
    
    def test_update_ai_user(self):
        """测试更新AI用户"""
        old_ai_id = self.chat_room.ai_user.session_id
        
        # 创建新的AI用户
        new_ai = create_ai_user("新AI助手")
        self.chat_room.update_ai_user(new_ai)
        
        # 检查更新结果
        assert self.chat_room.ai_user == new_ai
        assert new_ai.session_id in self.chat_room.online_users
        assert old_ai_id not in self.chat_room.online_users
    
    def test_broadcast_message_data(self):
        """测试广播消息数据"""
        user = create_user("session_123", "测试用户")
        self.chat_room.add_user(user)
        
        msg = create_user_message("测试用户", "测试消息")
        broadcast_data = self.chat_room.broadcast_message_data(msg)
        
        # 检查广播数据格式
        assert 'message' in broadcast_data
        assert 'online_users' in broadcast_data
        assert 'user_count' in broadcast_data
        assert 'timestamp' in broadcast_data
        
        assert broadcast_data['user_count'] == 2
        assert len(broadcast_data['online_users']) == 2
    
    def test_thread_safety(self):
        """测试线程安全性"""
        def add_users():
            for i in range(10):
                user = create_user(f"session_{i}", f"用户{i}")
                self.chat_room.add_user(user)
                time.sleep(0.001)  # 短暂延迟
        
        def add_messages():
            for i in range(10):
                msg = create_user_message(f"用户{i}", f"消息{i}")
                self.chat_room.add_message(msg)
                time.sleep(0.001)
        
        # 创建多个线程同时操作
        threads = []
        for _ in range(3):
            t1 = threading.Thread(target=add_users)
            t2 = threading.Thread(target=add_messages)
            threads.extend([t1, t2])
        
        # 启动所有线程
        for t in threads:
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证数据一致性（不应该有异常或数据损坏）
        assert len(self.chat_room.online_users) >= 1  # 至少有AI用户
        assert len(self.chat_room.message_history) >= 1  # 至少有欢迎消息


class TestChatRoomManager:
    """聊天室管理器测试类"""
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = ChatRoomManager()
        manager2 = ChatRoomManager()
        
        # 应该是同一个实例
        assert manager1 is manager2
        
        # 聊天室也应该是同一个
        room1 = manager1.get_chat_room()
        room2 = manager2.get_chat_room()
        assert room1 is room2
    
    def test_get_chat_room_function(self):
        """测试便捷函数"""
        room1 = get_chat_room()
        room2 = get_chat_room()
        
        # 应该返回同一个聊天室实例
        assert room1 is room2
        assert isinstance(room1, ChatRoomState)
    
    def test_reset_chat_room(self):
        """测试重置聊天室"""
        manager = ChatRoomManager()
        original_room = manager.get_chat_room()
        
        # 添加一些数据
        user = create_user("session_123", "测试用户")
        original_room.add_user(user)
        
        # 重置聊天室
        manager.reset_chat_room()
        new_room = manager.get_chat_room()
        
        # 应该是新的实例
        assert new_room is not original_room
        
        # 新聊天室应该是初始状态
        assert len(new_room.online_users) == 1  # 只有AI用户


class TestChatRoomValidator:
    """聊天室验证器测试类"""
    
    def test_validate_user_limit(self):
        """测试用户限制验证"""
        assert ChatRoomValidator.validate_user_limit(5, 10) is True
        assert ChatRoomValidator.validate_user_limit(10, 10) is False
        assert ChatRoomValidator.validate_user_limit(15, 10) is False
    
    def test_validate_message_limit(self):
        """测试消息限制验证"""
        assert ChatRoomValidator.validate_message_limit(50, 100) is True
        assert ChatRoomValidator.validate_message_limit(100, 100) is False
        assert ChatRoomValidator.validate_message_limit(150, 100) is False
    
    def test_can_user_join(self):
        """测试用户加入检查"""
        chat_room = ChatRoomState()
        
        # 正常情况应该可以加入
        can_join, message = ChatRoomValidator.can_user_join(chat_room, "新用户")
        assert can_join is True
        assert message == "可以加入"
        
        # 用户名重复应该不能加入
        user = create_user("session_123", "测试用户")
        chat_room.add_user(user)
        
        can_join, message = ChatRoomValidator.can_user_join(chat_room, "测试用户")
        assert can_join is False
        assert message == "用户名已被占用"
        
        # 用户数量超限应该不能加入
        chat_room.max_users = 2  # AI + 1个用户
        can_join, message = ChatRoomValidator.can_user_join(chat_room, "新用户2")
        assert can_join is False
        assert message == "聊天室已满"
    
    def test_validate_chat_room_state(self):
        """测试聊天室状态验证"""
        chat_room = ChatRoomState()
        
        # 正常状态应该没有问题
        issues = ChatRoomValidator.validate_chat_room_state(chat_room)
        assert len(issues) == 0
        
        # 移除AI用户（模拟异常状态）
        ai_session_id = chat_room.ai_user.session_id
        chat_room.online_users.pop(ai_session_id)
        
        issues = ChatRoomValidator.validate_chat_room_state(chat_room)
        assert len(issues) > 0
        assert any("AI用户不在在线用户列表中" in issue for issue in issues)


class TestChatRoomIntegration:
    """聊天室集成测试"""
    
    def test_complete_chat_flow(self):
        """测试完整的聊天流程"""
        chat_room = ChatRoomState()
        
        # 1. 用户加入
        user1 = create_user("session_1", "张三")
        user2 = create_user("session_2", "李四")
        
        assert chat_room.add_user(user1) is True
        assert chat_room.add_user(user2) is True
        assert chat_room.get_online_user_count() == 3  # AI + 2用户
        
        # 2. 用户发送消息
        msg1 = create_user_message("张三", "大家好！")
        msg2 = create_user_message("李四", "@AI 你好")
        
        chat_room.add_message(msg1)
        chat_room.add_message(msg2)
        
        # 3. AI回复
        ai_msg = create_ai_message("AI助手", "你好！很高兴见到你们。")
        chat_room.add_message(ai_msg)
        
        # 4. 验证状态
        stats = chat_room.get_chat_statistics()
        assert stats['online_users'] == 3
        assert stats['user_messages'] == 2
        assert stats['ai_messages'] == 1
        assert stats['ai_mentions'] == 1
        
        # 5. 用户离开
        removed_user = chat_room.remove_user("session_1")
        assert removed_user == user1
        assert chat_room.get_online_user_count() == 2
        
        # 6. 检查消息历史
        recent_messages = chat_room.get_recent_messages()
        assert len(recent_messages) >= 6  # 欢迎消息 + 2个加入通知 + 2条聊天 + AI回复 + 离开通知
    
    def test_concurrent_operations(self):
        """测试并发操作"""
        chat_room = ChatRoomState()
        results = []
        
        def user_operations(user_id):
            try:
                # 加入聊天室
                user = create_user(f"session_{user_id}", f"用户{user_id}")
                join_result = chat_room.add_user(user)
                
                if join_result:
                    # 发送消息
                    msg = create_user_message(f"用户{user_id}", f"来自用户{user_id}的消息")
                    chat_room.add_message(msg)
                    
                    # 获取在线用户
                    online_users = chat_room.get_online_users()
                    
                    # 离开聊天室
                    chat_room.remove_user(f"session_{user_id}")
                
                results.append(True)
            except Exception as e:
                results.append(False)
                print(f"用户{user_id}操作失败: {e}")
        
        # 创建多个线程模拟并发用户
        threads = []
        for i in range(10):
            t = threading.Thread(target=user_operations, args=(i,))
            threads.append(t)
        
        # 启动所有线程
        for t in threads:
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证结果
        assert len(results) == 10
        assert all(results)  # 所有操作都应该成功
        
        # 最终应该只剩AI用户
        assert chat_room.get_online_user_count() == 1
        assert chat_room.ai_user.session_id in chat_room.online_users