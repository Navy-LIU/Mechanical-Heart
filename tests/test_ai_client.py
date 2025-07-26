"""
AI客户端组件单元测试
"""
import pytest
import os
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.ai_client import (
    AIClient, AIClientManager, get_ai_client, AIResponseHandler, MockAIClient
)
from models.message import create_user_message, Message


class TestMockAIClient:
    """模拟AI客户端测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.ai_client = MockAIClient()
    
    def test_mock_client_initialization(self):
        """测试模拟客户端初始化"""
        assert self.ai_client.is_available() is True
        assert self.ai_client.model == "mock-model"
        assert self.ai_client.api_key == "mock-api-key"
        
        # 检查初始统计
        stats = self.ai_client.get_stats()
        assert stats['total_requests'] == 0
        assert stats['successful_requests'] == 0
        assert stats['failed_requests'] == 0
    
    def test_mock_get_ai_response_success(self):
        """测试模拟AI回复成功"""
        success, response = self.ai_client.get_ai_response("你好", username="测试用户")
        
        assert success is True
        assert isinstance(response, str)
        assert len(response) > 0
        
        # 检查统计更新
        stats = self.ai_client.get_stats()
        assert stats['total_requests'] == 1
        assert stats['successful_requests'] == 1
        assert stats['failed_requests'] == 0
    
    def test_mock_get_ai_response_error(self):
        """测试模拟AI回复错误"""
        success, response = self.ai_client.get_ai_response("错误测试", username="测试用户")
        
        assert success is False
        assert response == "模拟API错误"
        
        # 检查统计更新
        stats = self.ai_client.get_stats()
        assert stats['total_requests'] == 1
        assert stats['successful_requests'] == 0
        assert stats['failed_requests'] == 1
    
    def test_mock_multiple_responses(self):
        """测试多次模拟回复"""
        responses = []
        for i in range(3):
            success, response = self.ai_client.get_ai_response(f"消息{i}", username="测试用户")
            assert success is True
            responses.append(response)
        
        # 每次回复应该不同（循环使用预设回复）
        assert len(set(responses)) >= 1  # 至少有一个不同的回复
        
        # 检查统计
        stats = self.ai_client.get_stats()
        assert stats['total_requests'] == 3
        assert stats['successful_requests'] == 3
    
    def test_mock_format_ai_message(self):
        """测试格式化AI消息"""
        response = "这是AI的回复"
        message = self.ai_client.format_ai_message(response)
        
        assert isinstance(message, Message)
        assert message.content == response
        assert message.message_type == "ai"
        assert message.username == "AI助手"
    
    def test_mock_connection_test(self):
        """测试模拟连接测试"""
        success, message = self.ai_client.test_connection()
        assert success is True
        assert "成功" in message


class TestAIClient:
    """AI客户端测试类（使用模拟）"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 使用模拟的OpenAI客户端
        self.mock_openai_client = Mock()
        self.ai_client = AIClient(
            api_key="test-api-key",
            base_url="https://test.api.com",
            model="test-model"
        )
        self.ai_client.client = self.mock_openai_client
    
    def test_ai_client_initialization(self):
        """测试AI客户端初始化"""
        assert self.ai_client.api_key == "test-api-key"
        assert self.ai_client.base_url == "https://test.api.com"
        assert self.ai_client.model == "test-model"
        assert self.ai_client.is_available() is True
    
    def test_ai_client_initialization_without_openai(self):
        """测试没有OpenAI库时的初始化"""
        with patch('services.ai_client.OpenAI', None):
            client = AIClient(api_key="test-key")
            assert client.client is None
            assert client.is_available() is False
    
    def test_ai_client_initialization_without_api_key(self):
        """测试没有API密钥时的初始化"""
        with patch.dict(os.environ, {}, clear=True):
            client = AIClient()
            assert client.client is None
            assert client.is_available() is False
    
    def test_build_messages(self):
        """测试构建消息列表"""
        message = "你好"
        username = "测试用户"
        context = [
            {"role": "user", "content": "之前的消息"},
            {"role": "assistant", "content": "AI的回复"}
        ]
        
        messages = self.ai_client._build_messages(message, context, username)
        
        # 应该包含系统提示、上下文和当前消息
        assert len(messages) >= 3
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert f"{username}: {message}" in messages[-1]["content"]
    
    def test_get_system_prompt(self):
        """测试获取系统提示"""
        prompt = self.ai_client._get_system_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "AI助手" in prompt or "友好" in prompt
    
    @patch('time.sleep')  # 模拟sleep以加速测试
    def test_call_api_with_retry_success(self, mock_sleep):
        """测试API调用成功"""
        # 模拟成功的API响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "AI的回复"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 50
        
        self.mock_openai_client.chat.completions.create.return_value = mock_response
        
        messages = [{"role": "user", "content": "测试消息"}]
        success, response = self.ai_client._call_api_with_retry(messages)
        
        assert success is True
        assert response == "AI的回复"
        assert self.ai_client.stats['total_tokens_used'] == 50
    
    @patch('time.sleep')
    def test_call_api_with_retry_failure(self, mock_sleep):
        """测试API调用失败后重试"""
        # 模拟API调用失败
        self.mock_openai_client.chat.completions.create.side_effect = Exception("API错误")
        
        messages = [{"role": "user", "content": "测试消息"}]
        success, response = self.ai_client._call_api_with_retry(messages)
        
        assert success is False
        assert "不可用" in response or "错误" in response
        
        # 应该重试指定次数
        assert self.mock_openai_client.chat.completions.create.call_count == self.ai_client.max_retries
    
    def test_handle_api_error(self):
        """测试API错误处理"""
        test_cases = [
            (Exception("timeout"), "超时"),
            (Exception("rate limit exceeded"), "繁忙"),
            (Exception("authentication failed"), "配置错误"),
            (Exception("network error"), "网络"),
            (Exception("invalid request"), "格式有误"),
            (Exception("unknown error"), "不可用")
        ]
        
        for error, expected_keyword in test_cases:
            result = self.ai_client.handle_api_error(error)
            assert isinstance(result, str)
            assert len(result) > 0
            # 检查是否包含预期的关键词（不区分大小写）
            assert any(keyword in result for keyword in [expected_keyword, "AI", "服务"])
    
    def test_get_ai_response_empty_message(self):
        """测试空消息处理"""
        success, response = self.ai_client.get_ai_response("", username="测试用户")
        
        assert success is False
        assert "有效的消息" in response
    
    def test_get_ai_response_client_unavailable(self):
        """测试客户端不可用时的处理"""
        self.ai_client.client = None
        
        success, response = self.ai_client.get_ai_response("测试消息", username="测试用户")
        
        assert success is False
        assert "不可用" in response
    
    def test_format_ai_message(self):
        """测试格式化AI消息"""
        response = "这是AI的回复"
        ai_username = "智能助手"
        
        message = self.ai_client.format_ai_message(response, ai_username)
        
        assert isinstance(message, Message)
        assert message.content == response
        assert message.username == ai_username
        assert message.message_type == "ai"
    
    def test_get_stats(self):
        """测试获取统计信息"""
        stats = self.ai_client.get_stats()
        
        required_keys = [
            'total_requests', 'successful_requests', 'failed_requests',
            'total_tokens_used', 'success_rate', 'model', 'base_url', 'is_available'
        ]
        
        for key in required_keys:
            assert key in stats
        
        assert stats['model'] == "test-model"
        assert stats['base_url'] == "https://test.api.com"
        assert stats['is_available'] is True
    
    def test_reset_stats(self):
        """测试重置统计信息"""
        # 先设置一些统计数据
        self.ai_client.stats['total_requests'] = 10
        self.ai_client.stats['successful_requests'] = 8
        
        # 重置统计
        self.ai_client.reset_stats()
        
        # 验证统计已重置
        assert self.ai_client.stats['total_requests'] == 0
        assert self.ai_client.stats['successful_requests'] == 0
        assert self.ai_client.stats['failed_requests'] == 0
    
    def test_update_config(self):
        """测试更新配置"""
        original_max_tokens = self.ai_client.max_tokens
        original_temperature = self.ai_client.temperature
        
        # 更新配置
        self.ai_client.update_config(
            max_tokens=500,
            temperature=0.5,
            invalid_key="should_be_ignored"
        )
        
        # 验证配置已更新
        assert self.ai_client.max_tokens == 500
        assert self.ai_client.temperature == 0.5
        
        # 无效的配置键应该被忽略
        assert not hasattr(self.ai_client, 'invalid_key')


class TestAIClientManager:
    """AI客户端管理器测试类"""
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = AIClientManager()
        manager2 = AIClientManager()
        
        # 应该是同一个实例
        assert manager1 is manager2
        
        # AI客户端也应该是同一个
        client1 = manager1.get_ai_client()
        client2 = manager2.get_ai_client()
        assert client1 is client2
    
    def test_get_ai_client_function(self):
        """测试便捷函数"""
        client1 = get_ai_client()
        client2 = get_ai_client()
        
        # 应该返回同一个AI客户端实例
        assert client1 is client2
        assert isinstance(client1, AIClient)
    
    def test_reset_ai_client(self):
        """测试重置AI客户端"""
        manager = AIClientManager()
        original_client = manager.get_ai_client()
        
        # 重置客户端
        manager.reset_ai_client(api_key="new-key", model="new-model")
        new_client = manager.get_ai_client()
        
        # 应该是新的实例
        assert new_client is not original_client
        assert new_client.api_key == "new-key"
        assert new_client.model == "new-model"


class TestAIResponseHandler:
    """AI响应处理器测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.ai_client = MockAIClient()
        self.response_handler = AIResponseHandler(self.ai_client)
    
    def test_handle_ai_mention_success(self):
        """测试处理AI提及成功"""
        # 创建包含AI提及的消息
        message = create_user_message("测试用户", "@AI 你好")
        
        success, ai_message = self.response_handler.handle_ai_mention(message)
        
        assert success is True
        assert ai_message is not None
        assert isinstance(ai_message, Message)
        assert ai_message.message_type == "ai"
        assert len(ai_message.content) > 0
    
    def test_handle_ai_mention_no_mention(self):
        """测试处理不包含AI提及的消息"""
        # 创建普通消息
        message = create_user_message("测试用户", "普通消息")
        
        success, ai_message = self.response_handler.handle_ai_mention(message)
        
        assert success is False
        assert ai_message is None
    
    def test_handle_ai_mention_with_context(self):
        """测试带上下文的AI提及处理"""
        # 创建上下文消息
        context = [
            create_user_message("用户1", "之前的消息1"),
            create_user_message("用户2", "之前的消息2")
        ]
        
        # 创建AI提及消息
        message = create_user_message("测试用户", "@AI 基于上面的对话回复")
        
        success, ai_message = self.response_handler.handle_ai_mention(message, context)
        
        assert success is True
        assert ai_message is not None
        assert isinstance(ai_message, Message)
    
    def test_handle_ai_mention_error(self):
        """测试AI提及处理错误"""
        # 创建会导致错误的消息
        message = create_user_message("测试用户", "@AI 错误测试")
        
        success, ai_message = self.response_handler.handle_ai_mention(message)
        
        assert success is False
        assert ai_message is not None  # 应该返回错误消息
        assert ai_message.message_type == "ai"
        assert "错误" in ai_message.content or "API" in ai_message.content
    
    def test_get_ai_greeting(self):
        """测试获取AI问候消息"""
        # 带用户名的问候
        greeting_with_user = self.response_handler.get_ai_greeting("张三")
        assert isinstance(greeting_with_user, Message)
        assert greeting_with_user.message_type == "ai"
        assert "张三" in greeting_with_user.content
        assert "你好" in greeting_with_user.content or "欢迎" in greeting_with_user.content
        
        # 通用问候
        greeting_general = self.response_handler.get_ai_greeting()
        assert isinstance(greeting_general, Message)
        assert greeting_general.message_type == "ai"
        assert len(greeting_general.content) > 0
    
    def test_get_ai_farewell(self):
        """测试获取AI告别消息"""
        # 带用户名的告别
        farewell_with_user = self.response_handler.get_ai_farewell("李四")
        assert isinstance(farewell_with_user, Message)
        assert farewell_with_user.message_type == "ai"
        assert "李四" in farewell_with_user.content
        assert "再见" in farewell_with_user.content or "期待" in farewell_with_user.content
        
        # 通用告别
        farewell_general = self.response_handler.get_ai_farewell()
        assert isinstance(farewell_general, Message)
        assert farewell_general.message_type == "ai"
        assert len(farewell_general.content) > 0


class TestAIClientIntegration:
    """AI客户端集成测试"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.ai_client = MockAIClient()
        self.response_handler = AIResponseHandler(self.ai_client)
    
    def test_complete_ai_interaction_flow(self):
        """测试完整的AI交互流程"""
        # 1. 创建用户消息
        user_message = create_user_message("张三", "@AI 你好，请介绍一下自己")
        
        # 2. 处理AI提及
        success, ai_response = self.response_handler.handle_ai_mention(user_message)
        assert success is True
        assert ai_response is not None
        
        # 3. 验证AI回复
        assert ai_response.message_type == "ai"
        assert ai_response.username == "AI助手"
        assert len(ai_response.content) > 0
        
        # 4. 检查统计信息
        stats = self.ai_client.get_stats()
        assert stats['total_requests'] == 1
        assert stats['successful_requests'] == 1
        assert stats['success_rate'] == 100.0
    
    def test_multiple_ai_interactions(self):
        """测试多次AI交互"""
        messages = [
            "@AI 你好",
            "@AI 今天天气怎么样？",
            "@AI 谢谢你的帮助"
        ]
        
        responses = []
        for i, msg_content in enumerate(messages):
            user_msg = create_user_message(f"用户{i+1}", msg_content)
            success, ai_response = self.response_handler.handle_ai_mention(user_msg)
            
            assert success is True
            assert ai_response is not None
            responses.append(ai_response.content)
        
        # 验证每次回复都不同（模拟客户端会循环使用不同回复）
        assert len(responses) == 3
        
        # 检查最终统计
        stats = self.ai_client.get_stats()
        assert stats['total_requests'] == 3
        assert stats['successful_requests'] == 3
    
    def test_ai_error_handling_flow(self):
        """测试AI错误处理流程"""
        # 创建会导致错误的消息
        error_message = create_user_message("测试用户", "@AI 错误测试")
        
        success, ai_response = self.response_handler.handle_ai_mention(error_message)
        
        # 应该返回错误，但仍有AI回复消息
        assert success is False
        assert ai_response is not None
        assert ai_response.message_type == "ai"
        
        # 检查统计信息
        stats = self.ai_client.get_stats()
        assert stats['total_requests'] == 1
        assert stats['failed_requests'] == 1
        assert stats['success_rate'] == 0.0
    
    def test_ai_greeting_and_farewell_flow(self):
        """测试AI问候和告别流程"""
        # 获取问候消息
        greeting = self.response_handler.get_ai_greeting("新用户")
        assert greeting.message_type == "ai"
        assert "新用户" in greeting.content
        
        # 模拟一些对话
        user_msg = create_user_message("新用户", "@AI 你好")
        success, ai_response = self.response_handler.handle_ai_mention(user_msg)
        assert success is True
        
        # 获取告别消息
        farewell = self.response_handler.get_ai_farewell("新用户")
        assert farewell.message_type == "ai"
        assert "新用户" in farewell.content
        
        # 验证所有消息都是有效的AI消息
        for msg in [greeting, ai_response, farewell]:
            assert isinstance(msg, Message)
            assert msg.message_type == "ai"
            assert len(msg.content) > 0
    
    def test_ai_client_availability_check(self):
        """测试AI客户端可用性检查"""
        # 模拟客户端应该始终可用
        assert self.ai_client.is_available() is True
        
        # 测试连接
        success, message = self.ai_client.test_connection()
        assert success is True
        assert "成功" in message
        
        # 获取统计信息
        stats = self.ai_client.get_stats()
        assert stats['is_available'] is True
        assert 'model' in stats
        assert 'base_url' in stats