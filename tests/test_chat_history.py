"""
聊天历史组件单元测试
"""
import pytest
import os
import tempfile
import json
from datetime import datetime, timedelta

from services.chat_history import ChatHistory, ChatHistoryManager, get_chat_history
from models.message import create_user_message, create_ai_message, create_system_message


class TestChatHistory:
    """聊天历史测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 使用临时数据库文件
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.chat_history = ChatHistory(self.temp_db.name)
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        self.chat_history.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """测试数据库初始化"""
        # 数据库文件应该存在
        assert os.path.exists(self.temp_db.name)
        
        # 应该能够获取消息数量（初始为0）
        count = self.chat_history.get_message_count()
        assert count == 0
    
    def test_add_message(self):
        """测试添加消息"""
        message = create_user_message("测试用户", "这是一条测试消息")
        
        # 添加消息
        success = self.chat_history.add_message(message)
        assert success is True
        
        # 检查消息数量
        count = self.chat_history.get_message_count()
        assert count == 1
        
        # 获取消息并验证
        messages = self.chat_history.get_recent_messages(1)
        assert len(messages) == 1
        assert messages[0].content == "这是一条测试消息"
        assert messages[0].username == "测试用户"
        assert messages[0].message_type == "user"
    
    def test_add_multiple_messages(self):
        """测试添加多条消息"""
        messages = [
            create_user_message("用户1", "消息1"),
            create_ai_message("AI助手", "回复1"),
            create_system_message("系统通知"),
            create_user_message("用户2", "@AI 你好")
        ]
        
        # 添加所有消息
        for msg in messages:
            success = self.chat_history.add_message(msg)
            assert success is True
        
        # 检查消息数量
        count = self.chat_history.get_message_count()
        assert count == 4
        
        # 获取所有消息并验证顺序
        retrieved = self.chat_history.get_recent_messages(10)
        assert len(retrieved) == 4
        
        # 消息应该按时间顺序排列
        for i, original in enumerate(messages):
            assert retrieved[i].content == original.content
            assert retrieved[i].username == original.username
            assert retrieved[i].message_type == original.message_type
    
    def test_get_recent_messages_limit(self):
        """测试获取最近消息的数量限制"""
        # 添加10条消息
        for i in range(10):
            msg = create_user_message(f"用户{i}", f"消息{i}")
            self.chat_history.add_message(msg)
        
        # 获取最近5条消息
        messages = self.chat_history.get_recent_messages(5)
        assert len(messages) == 5
        
        # 应该是最新的5条消息
        for i, msg in enumerate(messages):
            expected_content = f"消息{5 + i}"  # 消息5-9
            assert expected_content in msg.content
    
    def test_get_messages_by_user(self):
        """测试按用户获取消息"""
        # 添加不同用户的消息
        messages = [
            create_user_message("张三", "张三的消息1"),
            create_user_message("李四", "李四的消息1"),
            create_user_message("张三", "张三的消息2"),
            create_ai_message("AI助手", "AI回复"),
            create_user_message("张三", "张三的消息3")
        ]
        
        for msg in messages:
            self.chat_history.add_message(msg)
        
        # 获取张三的消息
        zhang_messages = self.chat_history.get_messages_by_user("张三")
        assert len(zhang_messages) == 3
        
        for msg in zhang_messages:
            assert msg.username == "张三"
            assert "张三的消息" in msg.content
        
        # 获取李四的消息
        li_messages = self.chat_history.get_messages_by_user("李四")
        assert len(li_messages) == 1
        assert li_messages[0].content == "李四的消息1"
        
        # 获取不存在用户的消息
        empty_messages = self.chat_history.get_messages_by_user("不存在的用户")
        assert len(empty_messages) == 0
    
    def test_get_messages_by_timerange(self):
        """测试按时间范围获取消息"""
        now = datetime.now()
        
        # 添加不同时间的消息
        messages = [
            create_user_message("用户1", "1小时前的消息"),
            create_user_message("用户2", "30分钟前的消息"),
            create_user_message("用户3", "现在的消息")
        ]
        
        # 手动设置时间戳
        messages[0].timestamp = now - timedelta(hours=1)
        messages[1].timestamp = now - timedelta(minutes=30)
        messages[2].timestamp = now
        
        for msg in messages:
            self.chat_history.add_message(msg)
        
        # 获取最近45分钟的消息
        start_time = now - timedelta(minutes=45)
        end_time = now + timedelta(minutes=5)
        
        recent_messages = self.chat_history.get_messages_by_timerange(start_time, end_time)
        assert len(recent_messages) == 2  # 30分钟前和现在的消息
        
        # 验证消息内容
        contents = [msg.content for msg in recent_messages]
        assert "30分钟前的消息" in contents
        assert "现在的消息" in contents
        assert "1小时前的消息" not in contents
    
    def test_get_ai_mentioned_messages(self):
        """测试获取AI提及消息"""
        messages = [
            create_user_message("用户1", "普通消息"),
            create_user_message("用户2", "@AI 你好"),
            create_user_message("用户3", "另一条普通消息"),
            create_user_message("用户4", "@AI助手 请帮忙"),
            create_ai_message("AI助手", "我来帮你")
        ]
        
        for msg in messages:
            self.chat_history.add_message(msg)
        
        # 获取AI提及消息
        ai_messages = self.chat_history.get_ai_mentioned_messages()
        assert len(ai_messages) == 2
        
        # 验证都是提及AI的消息
        for msg in ai_messages:
            assert msg.mentions_ai is True
            assert "@AI" in msg.content
    
    def test_search_messages(self):
        """测试搜索消息"""
        messages = [
            create_user_message("用户1", "今天天气很好"),
            create_user_message("用户2", "明天天气怎么样"),
            create_user_message("用户3", "我喜欢晴天"),
            create_user_message("用户4", "雨天也不错")
        ]
        
        for msg in messages:
            self.chat_history.add_message(msg)
        
        # 搜索包含"天气"的消息
        weather_messages = self.chat_history.search_messages("天气")
        assert len(weather_messages) == 2
        
        for msg in weather_messages:
            assert "天气" in msg.content
        
        # 搜索包含"天"的消息
        day_messages = self.chat_history.search_messages("天")
        assert len(day_messages) == 4  # 所有消息都包含"天"
        
        # 搜索不存在的关键词
        empty_messages = self.chat_history.search_messages("不存在的关键词")
        assert len(empty_messages) == 0
    
    def test_get_user_message_count(self):
        """测试获取用户消息数量"""
        messages = [
            create_user_message("张三", "消息1"),
            create_user_message("张三", "消息2"),
            create_user_message("李四", "消息3"),
            create_ai_message("AI助手", "回复")
        ]
        
        for msg in messages:
            self.chat_history.add_message(msg)
        
        # 检查各用户的消息数量
        assert self.chat_history.get_user_message_count("张三") == 2
        assert self.chat_history.get_user_message_count("李四") == 1
        assert self.chat_history.get_user_message_count("AI助手") == 1
        assert self.chat_history.get_user_message_count("不存在的用户") == 0
    
    def test_clear_history(self):
        """测试清空历史"""
        # 添加一些消息
        for i in range(5):
            msg = create_user_message(f"用户{i}", f"消息{i}")
            self.chat_history.add_message(msg)
        
        # 确认消息已添加
        assert self.chat_history.get_message_count() == 5
        
        # 清空所有历史
        deleted_count = self.chat_history.clear_history()
        assert deleted_count == 5
        assert self.chat_history.get_message_count() == 0
    
    def test_clear_history_by_date(self):
        """测试按日期清空历史"""
        now = datetime.now()
        
        # 添加不同时间的消息
        old_msg = create_user_message("用户1", "旧消息")
        old_msg.timestamp = now - timedelta(days=2)
        
        new_msg = create_user_message("用户2", "新消息")
        new_msg.timestamp = now
        
        self.chat_history.add_message(old_msg)
        self.chat_history.add_message(new_msg)
        
        # 清空1天前的消息
        cutoff_date = now - timedelta(days=1)
        deleted_count = self.chat_history.clear_history(cutoff_date)
        
        assert deleted_count == 1
        assert self.chat_history.get_message_count() == 1
        
        # 剩余的应该是新消息
        remaining = self.chat_history.get_recent_messages(1)
        assert remaining[0].content == "新消息"
    
    def test_get_chat_statistics(self):
        """测试获取聊天统计"""
        messages = [
            create_user_message("用户1", "@AI 你好"),
            create_user_message("用户2", "普通消息"),
            create_ai_message("AI助手", "你好"),
            create_system_message("系统通知")
        ]
        
        for msg in messages:
            self.chat_history.add_message(msg)
        
        stats = self.chat_history.get_chat_statistics()
        
        assert stats['total_messages'] == 4
        assert stats['user_messages'] == 2
        assert stats['ai_messages'] == 1
        assert stats['system_messages'] == 1
        assert stats['ai_mentions'] == 1
        assert 'today_messages' in stats
        assert 'active_users_today' in stats
    
    def test_backup_and_restore(self):
        """测试备份和恢复"""
        # 添加一些消息
        original_messages = [
            create_user_message("用户1", "消息1"),
            create_ai_message("AI助手", "回复1"),
            create_system_message("系统通知")
        ]
        
        for msg in original_messages:
            self.chat_history.add_message(msg)
        
        # 备份到临时文件
        backup_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        backup_file.close()
        
        try:
            # 执行备份
            success = self.chat_history.backup_to_json(backup_file.name)
            assert success is True
            assert os.path.exists(backup_file.name)
            
            # 验证备份文件内容
            with open(backup_file.name, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            assert backup_data['message_count'] == 3
            assert len(backup_data['messages']) == 3
            
            # 清空数据库
            self.chat_history.clear_history()
            assert self.chat_history.get_message_count() == 0
            
            # 从备份恢复
            restored_count = self.chat_history.restore_from_json(backup_file.name)
            assert restored_count == 3
            assert self.chat_history.get_message_count() == 3
            
            # 验证恢复的消息
            restored_messages = self.chat_history.get_recent_messages(10)
            assert len(restored_messages) == 3
            
            # 验证消息内容（顺序可能不同）
            restored_contents = [msg.content for msg in restored_messages]
            original_contents = [msg.content for msg in original_messages]
            
            for content in original_contents:
                assert content in restored_contents
                
        finally:
            if os.path.exists(backup_file.name):
                os.unlink(backup_file.name)


class TestChatHistoryManager:
    """聊天历史管理器测试类"""
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = ChatHistoryManager()
        manager2 = ChatHistoryManager()
        
        # 应该是同一个实例
        assert manager1 is manager2
        
        # 聊天历史也应该是同一个
        history1 = manager1.get_chat_history()
        history2 = manager2.get_chat_history()
        assert history1 is history2
    
    def test_get_chat_history_function(self):
        """测试便捷函数"""
        history1 = get_chat_history()
        history2 = get_chat_history()
        
        # 应该返回同一个聊天历史实例
        assert history1 is history2
        assert isinstance(history1, ChatHistory)


class TestChatHistoryIntegration:
    """聊天历史集成测试"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.chat_history = ChatHistory(self.temp_db.name)
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        self.chat_history.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_complete_chat_session(self):
        """测试完整的聊天会话"""
        # 模拟一个完整的聊天会话
        session_messages = [
            create_system_message("用户张三加入了聊天室"),
            create_user_message("张三", "大家好！"),
            create_system_message("用户李四加入了聊天室"),
            create_user_message("李四", "你好张三！"),
            create_user_message("张三", "@AI 今天天气怎么样？"),
            create_ai_message("AI助手", "今天天气晴朗，温度适宜。"),
            create_user_message("李四", "谢谢AI助手！"),
            create_system_message("用户张三离开了聊天室")
        ]
        
        # 添加所有消息
        for msg in session_messages:
            success = self.chat_history.add_message(msg)
            assert success is True
        
        # 验证消息总数
        assert self.chat_history.get_message_count() == 8
        
        # 验证各类型消息数量
        stats = self.chat_history.get_chat_statistics()
        assert stats['user_messages'] == 3
        assert stats['ai_messages'] == 1
        assert stats['system_messages'] == 4
        assert stats['ai_mentions'] == 1
        
        # 验证用户消息数量
        assert self.chat_history.get_user_message_count("张三") == 2
        assert self.chat_history.get_user_message_count("李四") == 2
        assert self.chat_history.get_user_message_count("AI助手") == 1
        
        # 验证AI提及消息
        ai_mentions = self.chat_history.get_ai_mentioned_messages()
        assert len(ai_mentions) == 1
        assert "今天天气怎么样" in ai_mentions[0].content
        
        # 验证消息搜索
        weather_messages = self.chat_history.search_messages("天气")
        assert len(weather_messages) == 2  # 用户问题和AI回复
        
        # 验证最近消息获取
        recent = self.chat_history.get_recent_messages(3)
        assert len(recent) == 3
        assert recent[-1].content == "用户张三离开了聊天室"  # 最新消息
    
    def test_large_message_volume(self):
        """测试大量消息处理"""
        # 添加大量消息
        message_count = 1000
        
        for i in range(message_count):
            if i % 10 == 0:
                # 每10条消息中有一条AI提及
                msg = create_user_message(f"用户{i}", f"@AI 这是第{i}条消息")
            else:
                msg = create_user_message(f"用户{i}", f"这是第{i}条普通消息")
            
            success = self.chat_history.add_message(msg)
            assert success is True
        
        # 验证消息总数
        assert self.chat_history.get_message_count() == message_count
        
        # 验证AI提及消息数量
        ai_mentions = self.chat_history.get_ai_mentioned_messages(200)
        assert len(ai_mentions) == 100  # 每10条中有1条，共100条
        
        # 验证最近消息获取性能
        recent = self.chat_history.get_recent_messages(50)
        assert len(recent) == 50
        
        # 验证搜索功能
        search_results = self.chat_history.search_messages("普通消息", 100)
        assert len(search_results) == 100  # 限制返回100条
        
        # 验证统计信息
        stats = self.chat_history.get_chat_statistics()
        assert stats['total_messages'] == message_count
        assert stats['ai_mentions'] == 100
    
    def test_concurrent_operations(self):
        """测试并发操作"""
        import threading
        import time
        
        results = []
        
        def add_messages(thread_id, count):
            try:
                for i in range(count):
                    msg = create_user_message(f"线程{thread_id}", f"消息{i}")
                    success = self.chat_history.add_message(msg)
                    if success:
                        results.append(True)
                    time.sleep(0.001)  # 短暂延迟
            except Exception as e:
                results.append(False)
                print(f"线程{thread_id}异常: {e}")
        
        # 创建多个线程同时添加消息
        threads = []
        for i in range(5):
            t = threading.Thread(target=add_messages, args=(i, 20))
            threads.append(t)
        
        # 启动所有线程
        for t in threads:
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证结果
        assert len(results) == 100  # 5个线程 × 20条消息
        assert all(results)  # 所有操作都应该成功
        
        # 验证最终消息数量
        final_count = self.chat_history.get_message_count()
        assert final_count == 100