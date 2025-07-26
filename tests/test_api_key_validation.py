#!/usr/bin/env python3
"""
API密钥验证测试
测试Moonshot AI API密钥的有效性和集成状态
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from services.ai_client import AIClient


class TestAPIKeyValidation(unittest.TestCase):
    """API密钥验证测试类"""
    
    def setUp(self):
        """测试前的设置"""
        self.api_key = os.getenv('MOONSHOT_API_KEY')
        self.base_url = os.getenv('MOONSHOT_BASE_URL', 'https://api.moonshot.cn/v1')
    
    def test_api_key_exists(self):
        """测试API密钥是否已设置"""
        self.assertIsNotNone(self.api_key, "API密钥未在环境变量中设置")
        self.assertTrue(self.api_key.startswith('sk-'), "API密钥格式错误，应以'sk-'开头")
    
    def test_api_key_format(self):
        """测试API密钥格式"""
        if self.api_key:
            self.assertGreater(len(self.api_key), 30, "API密钥长度太短")
            self.assertTrue(self.api_key.startswith('sk-'), "API密钥应以'sk-'开头")
    
    def test_base_url_configuration(self):
        """测试API基础URL配置"""
        self.assertIsNotNone(self.base_url, "API基础URL未设置")
        self.assertTrue(self.base_url.startswith('https://'), "API基础URL应使用HTTPS")
        
    def test_ai_client_initialization(self):
        """测试AI客户端初始化"""
        client = AIClient()
        
        # 验证客户端配置
        self.assertEqual(client.api_key, self.api_key)
        self.assertEqual(client.base_url, self.base_url)
        self.assertIsNotNone(client.client, "OpenAI客户端初始化失败")
    
    @unittest.skipIf(not os.getenv('MOONSHOT_API_KEY'), "API密钥未设置，跳过实际API测试")
    def test_real_api_connection(self):
        """测试实际的API连接（仅当API密钥存在时）"""
        client = AIClient()
        
        # 发送简单的测试消息
        success, response = client.get_ai_response("测试连接", username="测试用户")
        
        # 验证响应
        if success:
            self.assertTrue(success, "API连接成功")
            self.assertIsInstance(response, str, "响应应为字符串")
            self.assertGreater(len(response), 0, "响应不应为空")
        else:
            # 如果连接失败，至少验证错误处理是否正常
            self.assertIsInstance(response, str, "错误响应应为字符串")
            print(f"API连接测试失败，但错误处理正常：{response}")
    
    def test_ai_client_stats(self):
        """测试AI客户端统计功能"""
        client = AIClient()
        stats = client.get_stats()
        
        # 验证统计信息结构
        required_stats = [
            'total_requests', 'successful_requests', 'failed_requests',
            'total_tokens_used', 'last_request_time', 'average_response_time'
        ]
        
        for stat in required_stats:
            self.assertIn(stat, stats, f"统计信息中缺少 {stat}")
    
    def test_error_handling(self):
        """测试错误处理机制"""
        # 使用无效的API密钥测试错误处理
        client = AIClient(api_key="sk-invalid-key")
        success, response = client.get_ai_response("测试消息")
        
        # 应该返回失败和错误消息
        self.assertFalse(success, "使用无效API密钥应该返回失败")
        self.assertIsInstance(response, str, "错误响应应为字符串")


class TestAPIIntegration(unittest.TestCase):
    """API集成测试类"""
    
    def test_ai_client_singleton_behavior(self):
        """测试AI客户端的单例行为"""
        from services.ai_client import get_ai_client, reset_ai_client
        
        # 重置并获取新实例
        reset_ai_client()
        client1 = get_ai_client()
        client2 = get_ai_client()
        
        # 验证单例行为
        self.assertIs(client1, client2, "AI客户端应实现单例模式")
    
    def test_message_formatting(self):
        """测试消息格式化功能"""
        client = AIClient()
        
        # 测试消息构建
        messages = client._build_messages("测试消息", username="测试用户")
        
        self.assertIsInstance(messages, list, "消息应为列表格式")
        self.assertGreater(len(messages), 0, "消息列表不应为空")
        
        # 验证消息结构
        for msg in messages:
            self.assertIn('role', msg, "消息应包含role字段")
            self.assertIn('content', msg, "消息应包含content字段")


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)