"""
消息广播机制单元测试
"""
import pytest
from datetime import datetime, timedelta
import time
from unittest.mock import Mock, patch

from services.broadcast_manager import (
    BroadcastManager, BroadcastType, get_broadcast_manager, SocketIOBroadcastAdapter
)
from models.message import create_user_message, create_ai_message, create_system_message


class TestBroadcastManager:
    """广播管理器测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.broadcast_manager = BroadcastManager()
    
    def test_broadcast_manager_initialization(self):
        """测试广播管理器初始化"""
        assert len(self.broadcast_manager._subscribers) == 0
        assert len(self.broadcast_manager._socket_subscribers) == 0
        assert len(self.broadcast_manager._room_subscribers) == 0
        assert self.broadcast_manager.stats['total_broadcasts'] == 0
        assert self.broadcast_manager.stats['subscribers_count'] == 0
    
    def test_subscribe_success(self):
        """测试成功订阅"""
        result = self.broadcast_manager.subscribe(
            socket_id="socket_123",
            username="测试用户",
            room="main",
            event_types=[BroadcastType.NEW_MESSAGE, BroadcastType.USER_JOIN]
        )
        
        assert result is True
        assert "socket_123" in self.broadcast_manager._socket_subscribers
        assert self.broadcast_manager.stats['subscribers_count'] == 1
        
        # 检查事件订阅
        assert "socket_123" in self.broadcast_manager._subscribers[BroadcastType.NEW_MESSAGE]
        assert "socket_123" in self.broadcast_manager._subscribers[BroadcastType.USER_JOIN]
        
        # 检查房间订阅
        assert "socket_123" in self.broadcast_manager._room_subscribers["main"]
        
        # 检查用户映射
        assert self.broadcast_manager._user_sockets["测试用户"] == "socket_123"
        assert self.broadcast_manager._socket_users["socket_123"] == "测试用户"
    
    def test_subscribe_all_events(self):
        """测试订阅所有事件类型"""
        result = self.broadcast_manager.subscribe("socket_123", "测试用户")
        
        assert result is True
        
        # 应该订阅所有事件类型
        for event_type in BroadcastType:
            assert "socket_123" in self.broadcast_manager._subscribers[event_type]
    
    def test_unsubscribe_success(self):
        """测试成功取消订阅"""
        # 先订阅
        self.broadcast_manager.subscribe("socket_123", "测试用户", "main")
        
        # 取消订阅
        result = self.broadcast_manager.unsubscribe("socket_123")
        
        assert result is True
        assert "socket_123" not in self.broadcast_manager._socket_subscribers
        assert self.broadcast_manager.stats['subscribers_count'] == 0
        
        # 检查清理
        for event_type in BroadcastType:
            assert "socket_123" not in self.broadcast_manager._subscribers[event_type]
        
        assert "socket_123" not in self.broadcast_manager._room_subscribers["main"]
        assert "测试用户" not in self.broadcast_manager._user_sockets
        assert "socket_123" not in self.broadcast_manager._socket_users
    
    def test_unsubscribe_nonexistent(self):
        """测试取消不存在的订阅"""
        result = self.broadcast_manager.unsubscribe("nonexistent_socket")
        assert result is False
    
    def test_broadcast_message(self):
        """测试广播消息"""
        # 添加订阅者
        self.broadcast_manager.subscribe("socket_1", "用户1", "main")
        self.broadcast_manager.subscribe("socket_2", "用户2", "main")
        
        # 创建消息
        message = create_user_message("用户1", "大家好！")
        
        # 广播消息
        result = self.broadcast_manager.broadcast_message(message, room="main")
        
        assert result['success'] is True
        assert result['target_count'] == 2
        assert result['successful_count'] == 2
        assert result['failed_count'] == 0
        assert result['event_type'] == BroadcastType.NEW_MESSAGE.value
        
        # 检查统计更新
        stats = self.broadcast_manager.get_stats()
        assert stats['total_broadcasts'] == 1
        assert stats['successful_broadcasts'] == 1
    
    def test_broadcast_message_with_ai_response(self):
        """测试广播包含AI回复的消息"""
        # 添加订阅者
        self.broadcast_manager.subscribe("socket_1", "用户1", "main")
        
        # 创建消息和AI回复
        message = create_user_message("用户1", "@AI 你好")
        ai_response = create_ai_message("AI助手", "你好！")
        
        # 广播消息
        result = self.broadcast_manager.broadcast_message(message, ai_response, room="main")
        
        assert result['success'] is True
        assert result['event_type'] == BroadcastType.MESSAGE_WITH_AI_RESPONSE.value
    
    def test_broadcast_user_join(self):
        """测试广播用户加入"""
        # 添加订阅者
        self.broadcast_manager.subscribe("socket_1", "用户1", "main")
        
        # 广播用户加入
        user_info = {"username": "新用户", "join_time": datetime.now().isoformat()}
        result = self.broadcast_manager.broadcast_user_join("新用户", user_info, "main")
        
        assert result['success'] is True
        assert result['event_type'] == BroadcastType.USER_JOIN.value
        assert result['target_count'] == 1
    
    def test_broadcast_user_leave(self):
        """测试广播用户离开"""
        # 添加订阅者
        self.broadcast_manager.subscribe("socket_1", "用户1", "main")
        
        # 广播用户离开
        user_info = {"username": "离开用户", "leave_time": datetime.now().isoformat()}
        result = self.broadcast_manager.broadcast_user_leave("离开用户", user_info, "main")
        
        assert result['success'] is True
        assert result['event_type'] == BroadcastType.USER_LEAVE.value
    
    def test_broadcast_user_list_update(self):
        """测试广播用户列表更新"""
        # 添加订阅者
        self.broadcast_manager.subscribe("socket_1", "用户1", "main")
        
        # 广播用户列表更新
        users = [
            {"username": "用户1", "is_ai": False},
            {"username": "AI助手", "is_ai": True}
        ]
        result = self.broadcast_manager.broadcast_user_list_update(users, 2, "main")
        
        assert result['success'] is True
        assert result['event_type'] == BroadcastType.USER_LIST_UPDATE.value
    
    def test_broadcast_system_notification(self):
        """测试广播系统通知"""
        # 添加订阅者
        self.broadcast_manager.subscribe("socket_1", "用户1", "main")
        
        # 广播系统通知
        result = self.broadcast_manager.broadcast_system_notification(
            "服务器将在5分钟后重启", "warning", "main"
        )
        
        assert result['success'] is True
        assert result['event_type'] == BroadcastType.SYSTEM_NOTIFICATION.value
    
    def test_broadcast_typing_indicator(self):
        """测试广播打字指示器"""
        # 添加订阅者
        self.broadcast_manager.subscribe("socket_1", "用户1", "main")
        self.broadcast_manager.subscribe("socket_2", "用户2", "main")
        
        # 广播打字指示器（应该排除发送者）
        result = self.broadcast_manager.broadcast_typing_indicator("用户1", True, "main")
        
        assert result['success'] is True
        assert result['event_type'] == BroadcastType.TYPING_INDICATOR.value
        assert result['target_count'] == 1  # 排除了发送者
    
    def test_broadcast_error_notification(self):
        """测试广播错误通知"""
        # 添加订阅者
        self.broadcast_manager.subscribe("socket_1", "用户1", "main")
        
        # 广播错误通知
        result = self.broadcast_manager.broadcast_error_notification(
            "连接超时", "TIMEOUT_ERROR", None, "main"
        )
        
        assert result['success'] is True
        assert result['event_type'] == BroadcastType.ERROR_NOTIFICATION.value
    
    def test_broadcast_error_notification_to_specific_socket(self):
        """测试向特定Socket广播错误通知"""
        # 添加订阅者
        self.broadcast_manager.subscribe("socket_1", "用户1", "main")
        
        # 向特定Socket广播错误通知
        result = self.broadcast_manager.broadcast_error_notification(
            "权限不足", "PERMISSION_ERROR", "socket_1", "main"
        )
        
        assert result['success'] is True
    
    def test_broadcast_to_different_rooms(self):
        """测试向不同房间广播"""
        # 添加不同房间的订阅者
        self.broadcast_manager.subscribe("socket_1", "用户1", "room1")
        self.broadcast_manager.subscribe("socket_2", "用户2", "room2")
        
        # 向room1广播
        message = create_user_message("用户1", "room1的消息")
        result = self.broadcast_manager.broadcast_message(message, room="room1")
        
        assert result['success'] is True
        assert result['target_count'] == 1  # 只有room1的用户
        
        # 向room2广播
        message = create_user_message("用户2", "room2的消息")
        result = self.broadcast_manager.broadcast_message(message, room="room2")
        
        assert result['success'] is True
        assert result['target_count'] == 1  # 只有room2的用户
    
    def test_broadcast_with_exclude_sockets(self):
        """测试排除特定Socket的广播"""
        # 添加订阅者
        self.broadcast_manager.subscribe("socket_1", "用户1", "main")
        self.broadcast_manager.subscribe("socket_2", "用户2", "main")
        self.broadcast_manager.subscribe("socket_3", "用户3", "main")
        
        # 广播时排除socket_2
        message = create_user_message("用户1", "测试消息")
        result = self.broadcast_manager.broadcast_message(
            message, room="main", exclude_sockets={"socket_2"}
        )
        
        assert result['success'] is True
        assert result['target_count'] == 2  # 排除了socket_2
    
    def test_broadcast_no_subscribers(self):
        """测试没有订阅者时的广播"""
        message = create_user_message("用户1", "没有人收到的消息")
        result = self.broadcast_manager.broadcast_message(message, room="empty_room")
        
        assert result['success'] is True
        assert result['target_count'] == 0
        assert result['successful_count'] == 0
    
    def test_get_subscribers_info(self):
        """测试获取订阅者信息"""
        # 添加订阅者
        self.broadcast_manager.subscribe("socket_1", "用户1", "main")
        self.broadcast_manager.subscribe("socket_2", "用户2", "room2")
        
        # 获取所有订阅者信息
        info = self.broadcast_manager.get_subscribers_info()
        
        assert info['total_subscribers'] == 2
        assert len(info['subscribers']) == 2
        assert 'main' in info['rooms']
        assert 'room2' in info['rooms']
        assert info['rooms']['main'] == 1
        assert info['rooms']['room2'] == 1
        
        # 获取特定房间的订阅者信息
        main_info = self.broadcast_manager.get_subscribers_info("main")
        assert main_info['total_subscribers'] == 1
        assert len(main_info['subscribers']) == 1
    
    def test_get_stats(self):
        """测试获取统计信息"""
        # 添加订阅者并执行一些广播
        self.broadcast_manager.subscribe("socket_1", "用户1", "main")
        
        message = create_user_message("用户1", "测试消息")
        self.broadcast_manager.broadcast_message(message)
        
        stats = self.broadcast_manager.get_stats()
        
        assert stats['total_broadcasts'] == 1
        assert stats['successful_broadcasts'] == 1
        assert stats['failed_broadcasts'] == 0
        assert stats['active_subscribers'] == 1
        assert stats['active_rooms'] == 1
        assert stats['success_rate'] == 100.0
        assert 'last_broadcast_time' in stats
    
    def test_get_broadcast_history(self):
        """测试获取广播历史"""
        # 添加订阅者
        self.broadcast_manager.subscribe("socket_1", "用户1", "main")
        
        # 执行几次广播
        message1 = create_user_message("用户1", "消息1")
        message2 = create_user_message("用户1", "消息2")
        
        self.broadcast_manager.broadcast_message(message1)
        self.broadcast_manager.broadcast_message(message2)
        
        # 获取广播历史
        history = self.broadcast_manager.get_broadcast_history(5)
        
        assert len(history) == 2
        assert history[0]['event_type'] == BroadcastType.NEW_MESSAGE.value
        assert history[1]['event_type'] == BroadcastType.NEW_MESSAGE.value
        assert 'timestamp' in history[0]
        assert 'target_count' in history[0]
    
    def test_cleanup_inactive_subscribers(self):
        """测试清理不活跃订阅者"""
        # 添加订阅者
        self.broadcast_manager.subscribe("socket_1", "用户1", "main")
        self.broadcast_manager.subscribe("socket_2", "用户2", "main")
        
        # 模拟一个订阅者长时间不活跃
        old_time = datetime.now() - timedelta(seconds=400)
        self.broadcast_manager._socket_subscribers["socket_1"]['last_activity'] = old_time
        
        # 清理不活跃订阅者（阈值300秒）
        cleaned_count = self.broadcast_manager.cleanup_inactive_subscribers(300)
        
        assert cleaned_count == 1
        assert "socket_1" not in self.broadcast_manager._socket_subscribers
        assert "socket_2" in self.broadcast_manager._socket_subscribers
    
    def test_reset_stats(self):
        """测试重置统计信息"""
        # 添加订阅者并执行广播
        self.broadcast_manager.subscribe("socket_1", "用户1", "main")
        message = create_user_message("用户1", "测试消息")
        self.broadcast_manager.broadcast_message(message)
        
        # 检查有统计数据
        stats_before = self.broadcast_manager.get_stats()
        assert stats_before['total_broadcasts'] > 0
        
        # 重置统计
        self.broadcast_manager.reset_stats()
        
        # 检查统计已重置
        stats_after = self.broadcast_manager.get_stats()
        assert stats_after['total_broadcasts'] == 0
        assert stats_after['successful_broadcasts'] == 0
        assert stats_after['failed_broadcasts'] == 0
        assert len(self.broadcast_manager.get_broadcast_history()) == 0


class TestBroadcastManagerSingleton:
    """广播管理器单例测试"""
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = get_broadcast_manager()
        manager2 = get_broadcast_manager()
        
        # 应该是同一个实例
        assert manager1 is manager2
        assert isinstance(manager1, BroadcastManager)


class TestSocketIOBroadcastAdapter:
    """SocketIO广播适配器测试"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.mock_socketio = Mock()
        self.broadcast_manager = BroadcastManager()
        self.adapter = SocketIOBroadcastAdapter(self.mock_socketio, self.broadcast_manager)
    
    def test_adapter_initialization(self):
        """测试适配器初始化"""
        assert self.adapter.socketio is self.mock_socketio
        assert self.adapter.broadcast_manager is self.broadcast_manager
        
        # 检查发送方法是否被重写
        assert self.broadcast_manager._send_to_socket == self.adapter._send_to_socket_impl
    
    def test_handle_connect(self):
        """测试处理连接"""
        result = self.adapter.handle_connect("socket_123", "测试用户", "main")
        
        assert result is True
        assert "socket_123" in self.broadcast_manager._socket_subscribers
    
    def test_handle_disconnect(self):
        """测试处理断开"""
        # 先连接
        self.adapter.handle_connect("socket_123", "测试用户", "main")
        
        # 断开连接
        result = self.adapter.handle_disconnect("socket_123")
        
        assert result is True
        assert "socket_123" not in self.broadcast_manager._socket_subscribers
    
    def test_handle_join_room(self):
        """测试处理加入房间"""
        # 先连接到main房间
        self.adapter.handle_connect("socket_123", "测试用户", "main")
        
        # 加入新房间
        result = self.adapter.handle_join_room("socket_123", "new_room")
        
        assert result is True
        
        # 检查房间变更
        subscriber_info = self.broadcast_manager._socket_subscribers["socket_123"]
        assert subscriber_info['room'] == "new_room"
    
    def test_handle_leave_room(self):
        """测试处理离开房间"""
        # 先连接
        self.adapter.handle_connect("socket_123", "测试用户", "main")
        
        # 离开房间
        result = self.adapter.handle_leave_room("socket_123")
        
        assert result is True
        assert "socket_123" not in self.broadcast_manager._socket_subscribers
    
    def test_send_to_socket_impl(self):
        """测试实际的Socket发送实现"""
        # 先添加订阅者
        self.broadcast_manager.subscribe("socket_123", "测试用户", "main")
        
        # 发送数据
        test_data = {"type": "test", "message": "测试消息"}
        result = self.adapter._send_to_socket_impl("socket_123", test_data)
        
        assert result['success'] is True
        assert result['socket_id'] == "socket_123"
        
        # 检查SocketIO的emit方法是否被调用
        self.mock_socketio.emit.assert_called_once_with(
            'broadcast_message',
            test_data,
            room="socket_123"
        )
    
    def test_send_to_socket_impl_error(self):
        """测试Socket发送实现错误处理"""
        # 模拟SocketIO emit方法抛出异常
        self.mock_socketio.emit.side_effect = Exception("发送失败")
        
        # 先添加订阅者
        self.broadcast_manager.subscribe("socket_123", "测试用户", "main")
        
        # 发送数据
        test_data = {"type": "test", "message": "测试消息"}
        result = self.adapter._send_to_socket_impl("socket_123", test_data)
        
        assert result['success'] is False
        assert "发送失败" in result['error']


class TestBroadcastIntegration:
    """广播机制集成测试"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.broadcast_manager = BroadcastManager()
    
    def test_complete_chat_broadcast_flow(self):
        """测试完整的聊天广播流程"""
        # 1. 用户连接和订阅
        self.broadcast_manager.subscribe("socket_1", "张三", "main")
        self.broadcast_manager.subscribe("socket_2", "李四", "main")
        self.broadcast_manager.subscribe("socket_3", "王五", "main")
        
        # 2. 广播用户加入通知
        user_info = {"username": "张三", "join_time": datetime.now().isoformat()}
        join_result = self.broadcast_manager.broadcast_user_join("张三", user_info, "main")
        assert join_result['success'] is True
        assert join_result['target_count'] == 3
        
        # 3. 广播用户列表更新
        users = [
            {"username": "张三", "is_ai": False},
            {"username": "李四", "is_ai": False},
            {"username": "王五", "is_ai": False},
            {"username": "AI助手", "is_ai": True}
        ]
        list_result = self.broadcast_manager.broadcast_user_list_update(users, 4, "main")
        assert list_result['success'] is True
        
        # 4. 广播普通消息
        message = create_user_message("张三", "大家好！")
        msg_result = self.broadcast_manager.broadcast_message(message, room="main")
        assert msg_result['success'] is True
        assert msg_result['target_count'] == 3
        
        # 5. 广播AI交互消息
        ai_message = create_user_message("李四", "@AI 你好")
        ai_response = create_ai_message("AI助手", "你好李四！")
        ai_result = self.broadcast_manager.broadcast_message(ai_message, ai_response, "main")
        assert ai_result['success'] is True
        assert ai_result['event_type'] == BroadcastType.MESSAGE_WITH_AI_RESPONSE.value
        
        # 6. 广播系统通知
        sys_result = self.broadcast_manager.broadcast_system_notification(
            "服务器将在5分钟后重启", "warning", "main"
        )
        assert sys_result['success'] is True
        
        # 7. 用户离开
        leave_result = self.broadcast_manager.broadcast_user_leave("王五", {"username": "王五"}, "main")
        assert leave_result['success'] is True
        
        # 验证最终统计
        stats = self.broadcast_manager.get_stats()
        assert stats['total_broadcasts'] == 6
        assert stats['successful_broadcasts'] == 6
        assert stats['success_rate'] == 100.0
    
    def test_multi_room_broadcast_flow(self):
        """测试多房间广播流程"""
        # 创建不同房间的用户
        self.broadcast_manager.subscribe("socket_1", "用户1", "room1")
        self.broadcast_manager.subscribe("socket_2", "用户2", "room1")
        self.broadcast_manager.subscribe("socket_3", "用户3", "room2")
        self.broadcast_manager.subscribe("socket_4", "用户4", "room2")
        
        # 向room1广播
        message1 = create_user_message("用户1", "room1的消息")
        result1 = self.broadcast_manager.broadcast_message(message1, room="room1")
        assert result1['target_count'] == 2
        
        # 向room2广播
        message2 = create_user_message("用户3", "room2的消息")
        result2 = self.broadcast_manager.broadcast_message(message2, room="room2")
        assert result2['target_count'] == 2
        
        # 向不存在的房间广播
        message3 = create_user_message("用户1", "空房间消息")
        result3 = self.broadcast_manager.broadcast_message(message3, room="empty_room")
        assert result3['target_count'] == 0
        
        # 验证房间信息
        info = self.broadcast_manager.get_subscribers_info()
        assert info['rooms']['room1'] == 2
        assert info['rooms']['room2'] == 2
    
    def test_error_handling_and_recovery(self):
        """测试错误处理和恢复"""
        # 添加订阅者
        self.broadcast_manager.subscribe("socket_1", "用户1", "main")
        self.broadcast_manager.subscribe("socket_2", "用户2", "main")
        
        # 模拟发送失败的情况
        original_send = self.broadcast_manager._send_to_socket
        
        def mock_send_with_failure(socket_id, data):
            if socket_id == "socket_1":
                return {'success': False, 'error': '模拟发送失败', 'socket_id': socket_id}
            else:
                return original_send(socket_id, data)
        
        self.broadcast_manager._send_to_socket = mock_send_with_failure
        
        # 执行广播
        message = create_user_message("用户1", "测试消息")
        result = self.broadcast_manager.broadcast_message(message, room="main")
        
        # 验证部分成功的结果
        assert result['success'] is True
        assert result['target_count'] == 2
        assert result['successful_count'] == 1
        assert result['failed_count'] == 1
        
        # 恢复原始发送方法
        self.broadcast_manager._send_to_socket = original_send
    
    def test_concurrent_broadcast_operations(self):
        """测试并发广播操作"""
        import threading
        
        # 添加多个订阅者
        for i in range(10):
            self.broadcast_manager.subscribe(f"socket_{i}", f"用户{i}", "main")
        
        results = []
        
        def broadcast_messages(thread_id, count):
            for i in range(count):
                try:
                    message = create_user_message(f"用户{thread_id}", f"线程{thread_id}消息{i}")
                    result = self.broadcast_manager.broadcast_message(message, room="main")
                    results.append(result['success'])
                    time.sleep(0.001)  # 短暂延迟
                except Exception as e:
                    results.append(False)
                    print(f"广播失败: {e}")
        
        # 创建多个线程同时广播
        threads = []
        for i in range(3):
            t = threading.Thread(target=broadcast_messages, args=(i, 5))
            threads.append(t)
        
        # 启动所有线程
        for t in threads:
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证结果
        assert len(results) == 15  # 3个线程 × 5条消息
        assert all(results)  # 所有广播都应该成功
        
        # 验证最终统计
        stats = self.broadcast_manager.get_stats()
        assert stats['total_broadcasts'] >= 15