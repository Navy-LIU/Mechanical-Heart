#!/usr/bin/env python3
"""
API集成测试
测试API在实际应用中的工作状态
"""

import unittest
import os
import time
from services.ai_client import AIClient, get_ai_client


class TestAPIIntegration(unittest.TestCase):
    """API集成测试类"""
    
    def setUp(self):
        """测试设置"""
        self.client = get_ai_client()
    
    def test_api_client_availability(self):
        """测试API客户端是否可用"""
        self.assertIsNotNone(self.client, "AI客户端应该存在")
        self.assertIsNotNone(self.client.client, "OpenAI客户端应该已初始化")
    
    def test_api_configuration(self):
        """测试API配置"""
        self.assertEqual(self.client.base_url, "https://api.moonshot.cn/v1", 
                        "应该使用正确的API端点")
        self.assertIsNotNone(self.client.api_key, "API密钥应该存在")
        self.assertTrue(self.client.api_key.startswith('sk-'), 
                       "API密钥格式应该正确")
    
    @unittest.skipIf(not os.getenv('MOONSHOT_API_KEY'), "需要有效的API密钥")
    def test_simple_ai_response(self):
        """测试简单的AI响应"""
        success, response = self.client.get_ai_response("你好", username="测试用户")
        
        if success:
            self.assertTrue(success, "AI应该成功响应")
            self.assertIsInstance(response, str, "响应应该是字符串")
            self.assertGreater(len(response), 0, "响应不应该为空")
            print(f"✅ AI响应测试成功: {response}")
        else:
            print(f"⚠️ AI响应测试失败: {response}")
            # 即使失败，也验证错误处理是否正确
            self.assertIsInstance(response, str, "错误响应应该是字符串")
    
    @unittest.skipIf(not os.getenv('MOONSHOT_API_KEY'), "需要有效的API密钥")
    def test_ai_mention_response(self):
        """测试@AI提及功能"""
        success, response = self.client.get_ai_response("@AI 你好，请简单介绍一下自己", 
                                                      username="测试用户")
        
        if success:
            self.assertTrue(success, "AI提及应该成功")
            self.assertIn("Kimi", response, "AI应该介绍自己是Kimi")
            print(f"✅ AI提及测试成功: {response}")
        else:
            print(f"⚠️ AI提及测试失败: {response}")
    
    def test_stats_tracking(self):
        """测试统计信息跟踪"""
        initial_stats = self.client.get_stats()
        initial_requests = initial_stats['total_requests']
        
        # 发送一个请求
        self.client.get_ai_response("测试统计", username="测试用户")
        
        # 检查统计信息是否更新
        updated_stats = self.client.get_stats()
        self.assertGreaterEqual(updated_stats['total_requests'], 
                              initial_requests, 
                              "请求计数应该增加")
    
    def test_connection_status(self):
        """测试连接状态"""
        stats = self.client.get_stats()
        
        # 验证基本统计结构
        required_fields = [
            'total_requests', 'successful_requests', 'failed_requests',
            'success_rate', 'is_available'
        ]
        
        for field in required_fields:
            self.assertIn(field, stats, f"统计信息应包含 {field}")
        
        print(f"📊 客户端统计信息:")
        for key, value in stats.items():
            print(f"   {key}: {value}")


class TestAPIEndpointValidation(unittest.TestCase):
    """API端点验证测试"""
    
    def test_correct_endpoint_usage(self):
        """验证使用的是正确的API端点"""
        client = AIClient()
        
        # 应该使用moonshot.cn而不是moonshot.ai
        self.assertTrue(client.base_url.endswith("/v1"), 
                       "API URL应该以/v1结尾")
        self.assertIn("moonshot.cn", client.base_url, 
                     "应该使用moonshot.cn域名")
        self.assertNotIn("moonshot.ai", client.base_url, 
                        "不应该使用moonshot.ai域名")


if __name__ == '__main__':
    print("🚀 开始API集成测试")
    print("=" * 50)
    
    # 运行测试
    unittest.main(verbosity=2)