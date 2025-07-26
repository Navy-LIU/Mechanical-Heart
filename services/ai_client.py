"""
AI客户端组件
集成月之暗面API，处理AI请求和响应，包含错误处理和重试机制
"""
import os
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from models.message import Message, create_ai_message

# 配置日志
logger = logging.getLogger(__name__)


class AIClient:
    """AI客户端，用于与月之暗面API交互"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        """
        初始化AI客户端
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 使用的模型名称
        """
        self.api_key = api_key or os.getenv('MOONSHOT_API_KEY') or 'sk-CvSKjI19yjpqBQfSy7zNzbHSryd2wmhmj8kHwWJmtKJI1zVs'
        self.base_url = base_url or os.getenv('MOONSHOT_BASE_URL', 'https://api.moonshot.cn/v1')
        self.model = model or os.getenv('MOONSHOT_MODEL', 'kimi-k2-0711-preview')
        
        # 配置参数
        self.max_retries = int(os.getenv('AI_MAX_RETRIES', 3))
        self.retry_delay = float(os.getenv('AI_RETRY_DELAY', 1.0))
        self.timeout = float(os.getenv('AI_TIMEOUT', 30.0))
        self.max_tokens = int(os.getenv('AI_MAX_TOKENS', 1000))
        self.temperature = float(os.getenv('AI_TEMPERATURE', 0.6))
        
        # 初始化OpenAI客户端
        self.client = None
        self._init_client()
        
        # 统计信息
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens_used': 0,
            'last_request_time': None,
            'average_response_time': 0.0
        }
    
    def _init_client(self):
        """初始化OpenAI客户端"""
        try:
            if not OpenAI:
                raise ImportError("OpenAI库未安装，请运行: pip install openai")
            
            if not self.api_key:
                raise ValueError("API密钥未设置，请设置MOONSHOT_API_KEY环境变量")
            
            # 使用简化的初始化参数，显式设置不使用代理
            import httpx
            http_client = httpx.Client(trust_env=False)  # 禁用环境代理设置
            
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                http_client=http_client
            )
            
            logger.info(f"AI客户端初始化成功: {self.base_url}")
            
        except Exception as e:
            import traceback
            logger.error(f"AI客户端初始化失败: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            self.client = None
    
    def get_ai_response(self, message: str, context: List[Dict[str, str]] = None, username: str = "用户") -> Tuple[bool, str]:
        """
        获取AI回复
        
        Args:
            message: 用户消息内容
            context: 对话上下文（可选）
            username: 用户名
            
        Returns:
            (成功标志, AI回复内容)
        """
        if not self.client:
            return False, "AI服务暂时不可用，请稍后再试。"
        
        if not message or not message.strip():
            return False, "请输入有效的消息内容。"
        
        start_time = time.time()
        self.stats['total_requests'] += 1
        
        try:
            # 构建消息列表
            messages = self._build_messages(message, context, username)
            
            # 调用API
            success, response = self._call_api_with_retry(messages)
            
            if success:
                self.stats['successful_requests'] += 1
                self._update_response_time(start_time)
                return True, response
            else:
                self.stats['failed_requests'] += 1
                return False, response
                
        except Exception as e:
            self.stats['failed_requests'] += 1
            logger.error(f"获取AI回复失败: {e}")
            return False, self.handle_api_error(e)
    
    def _build_messages(self, message: str, context: List[Dict[str, str]] = None, username: str = "用户") -> List[Dict[str, str]]:
        """构建API请求的消息列表"""
        messages = []
        
        # 添加系统提示
        system_prompt = self._get_system_prompt()
        messages.append({"role": "system", "content": system_prompt})
        
        # 添加上下文消息（保持对话历史）
        if context:
            # 保留更多上下文以支持多轮对话，但限制在合理范围内
            recent_context = context[-10:] if len(context) > 10 else context
            for ctx_msg in recent_context:
                # 确保消息格式正确
                if isinstance(ctx_msg, dict) and 'role' in ctx_msg and 'content' in ctx_msg:
                    messages.append(ctx_msg)
        
        # 添加当前用户消息，清理@AI标记
        clean_message = message.replace('@AI', '').strip()
        user_message = f"{username}: {clean_message}"
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。

作为聊天室的AI助手，请注意：
1. 保持友好、热情的沟通风格
2. 回复简洁明了，通常不超过200字
3. 适当使用表情符号增加亲和力
4. 记住你在多用户聊天环境中，可能有多人同时在线
5. 对于技术问题提供准确信息，不确定时诚实说明
6. 你能记住对话历史，可以进行多轮对话
7. 回复时无需在前面加"AI:"等标识，直接回复内容即可。"""
    
    def _call_api_with_retry(self, messages: List[Dict[str, str]]) -> Tuple[bool, str]:
        """带重试机制的API调用"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"API调用尝试 {attempt + 1}/{self.max_retries}")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    stream=False
                )
                
                # 提取回复内容
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    if content:
                        # 更新token使用统计
                        if hasattr(response, 'usage') and response.usage:
                            self.stats['total_tokens_used'] += response.usage.total_tokens
                        
                        self.stats['last_request_time'] = datetime.now()
                        return True, content.strip()
                
                return False, "AI回复为空，请重试。"
                
            except Exception as e:
                last_error = e
                logger.warning(f"API调用失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    # 指数退避重试
                    delay = self.retry_delay * (2 ** attempt)
                    logger.debug(f"等待 {delay} 秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"API调用最终失败: {e}")
        
        return False, self.handle_api_error(last_error)
    
    def handle_api_error(self, error: Exception) -> str:
        """处理API错误，返回用户友好的错误消息"""
        error_str = str(error).lower()
        
        if 'timeout' in error_str:
            return "AI响应超时，请稍后再试。⏰"
        elif 'rate limit' in error_str or 'quota' in error_str:
            return "AI服务繁忙，请稍后再试。🚦"
        elif 'authentication' in error_str or 'api key' in error_str:
            return "AI服务配置错误，请联系管理员。🔑"
        elif 'network' in error_str or 'connection' in error_str:
            return "网络连接问题，请检查网络后重试。🌐"
        elif 'invalid' in error_str:
            return "请求格式有误，请重新输入。📝"
        else:
            return f"AI服务暂时不可用，请稍后再试。🤖"
    
    def format_ai_message(self, response: str, ai_username: str = "AI助手") -> Message:
        """格式化AI回复为消息对象"""
        return create_ai_message(ai_username, response)
    
    def _update_response_time(self, start_time: float):
        """更新平均响应时间"""
        response_time = time.time() - start_time
        
        if self.stats['successful_requests'] == 1:
            self.stats['average_response_time'] = response_time
        else:
            # 计算移动平均
            alpha = 0.1  # 平滑因子
            self.stats['average_response_time'] = (
                alpha * response_time + 
                (1 - alpha) * self.stats['average_response_time']
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取客户端统计信息"""
        return {
            **self.stats,
            'success_rate': (
                self.stats['successful_requests'] / max(self.stats['total_requests'], 1) * 100
            ),
            'model': self.model,
            'base_url': self.base_url,
            'is_available': self.is_available()
        }
    
    def is_available(self) -> bool:
        """检查AI服务是否可用"""
        return self.client is not None and bool(self.api_key)
    
    def test_connection(self) -> Tuple[bool, str]:
        """测试API连接"""
        if not self.is_available():
            return False, "AI客户端未正确初始化"
        
        try:
            success, response = self.get_ai_response("你好", username="测试用户")
            if success:
                return True, "连接测试成功"
            else:
                return False, f"连接测试失败: {response}"
        except Exception as e:
            return False, f"连接测试异常: {str(e)}"
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens_used': 0,
            'last_request_time': None,
            'average_response_time': 0.0
        }
        logger.info("AI客户端统计信息已重置")
    
    def update_config(self, **kwargs):
        """更新配置参数"""
        config_map = {
            'max_retries': 'max_retries',
            'retry_delay': 'retry_delay',
            'timeout': 'timeout',
            'max_tokens': 'max_tokens',
            'temperature': 'temperature',
            'model': 'model'
        }
        
        updated = []
        for key, value in kwargs.items():
            if key in config_map:
                setattr(self, config_map[key], value)
                updated.append(key)
        
        if updated:
            logger.info(f"AI客户端配置已更新: {updated}")
            # 如果更新了关键配置，重新初始化客户端
            if any(key in ['api_key', 'base_url', 'timeout'] for key in updated):
                self._init_client()
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"AIClient(model={self.model}, available={self.is_available()})"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"AIClient(model='{self.model}', base_url='{self.base_url}', "
                f"available={self.is_available()}, requests={self.stats['total_requests']})")


class AIClientManager:
    """AI客户端管理器（单例模式）"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.ai_client = AIClient()
            self._initialized = True
    
    def get_ai_client(self) -> AIClient:
        """获取AI客户端实例"""
        return self.ai_client
    
    def reset_ai_client(self, **kwargs):
        """重置AI客户端（用于测试或配置更新）"""
        self.ai_client = AIClient(**kwargs)
    
    @classmethod
    def get_instance(cls) -> 'AIClientManager':
        """获取管理器实例"""
        return cls()


def get_ai_client() -> AIClient:
    """获取全局AI客户端实例的便捷函数"""
    return AIClientManager.get_instance().get_ai_client()


class AIResponseHandler:
    """AI响应处理器"""
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
    
    def handle_ai_mention(self, message: Message, context: List[Message] = None) -> Tuple[bool, Optional[Message]]:
        """
        处理AI提及消息
        
        Args:
            message: 包含AI提及的消息
            context: 对话上下文消息列表
            
        Returns:
            (成功标志, AI回复消息对象)
        """
        if not message.mentions_ai:
            return False, None
        
        try:
            # 提取AI输入内容
            ai_input = message.extract_ai_mention_content()
            if not ai_input:
                ai_input = "你好！"
            
            # 构建上下文
            context_messages = []
            if context:
                for ctx_msg in context[-3:]:  # 最近3条消息作为上下文
                    role = "assistant" if ctx_msg.is_from_ai() else "user"
                    content = f"{ctx_msg.username}: {ctx_msg.content}"
                    context_messages.append({"role": role, "content": content})
            
            # 获取AI回复
            success, response = self.ai_client.get_ai_response(
                ai_input, 
                context_messages, 
                message.username
            )
            
            if success:
                ai_message = self.ai_client.format_ai_message(response)
                return True, ai_message
            else:
                # 创建错误回复消息
                error_message = self.ai_client.format_ai_message(response)
                return False, error_message
                
        except Exception as e:
            logger.error(f"处理AI提及失败: {e}")
            error_response = "抱歉，我现在无法回复，请稍后再试。😅"
            error_message = self.ai_client.format_ai_message(error_response)
            return False, error_message
    
    def get_ai_greeting(self, username: str = None) -> Message:
        """获取AI问候消息"""
        if username:
            greeting = f"你好 {username}！我是AI助手，有什么可以帮助你的吗？😊"
        else:
            greeting = "大家好！我是AI助手，随时为大家服务！有问题请@我哦～ 🤖✨"
        
        return self.ai_client.format_ai_message(greeting)
    
    def get_ai_farewell(self, username: str = None) -> Message:
        """获取AI告别消息"""
        if username:
            farewell = f"再见 {username}！期待下次聊天！👋"
        else:
            farewell = "大家聊天愉快！我随时在这里等待大家的问题～ 😊"
        
        return self.ai_client.format_ai_message(farewell)


class MockAIClient(AIClient):
    """模拟AI客户端（用于测试）"""
    
    def __init__(self):
        # 不调用父类初始化，避免需要真实API密钥
        self.api_key = "mock-api-key"
        self.base_url = "mock://api.example.com"
        self.model = "mock-model"
        self.client = "mock-client"
        
        self.max_retries = 1
        self.retry_delay = 0.1
        self.timeout = 5.0
        self.max_tokens = 100
        self.temperature = 0.7
        
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens_used': 0,
            'last_request_time': None,
            'average_response_time': 0.0
        }
        
        # 模拟响应
        self.mock_responses = [
            "你好！我是AI助手，很高兴为你服务！😊",
            "这是一个很好的问题，让我来帮你解答。",
            "感谢你的提问！我会尽力帮助你。",
            "有什么其他问题吗？我随时为你服务！",
            "希望我的回答对你有帮助！✨"
        ]
        self.response_index = 0
    
    def get_ai_response(self, message: str, context: List[Dict[str, str]] = None, username: str = "用户") -> Tuple[bool, str]:
        """模拟AI回复"""
        import time
        time.sleep(0.1)  # 模拟网络延迟
        
        self.stats['total_requests'] += 1
        
        # 检查空消息
        if not message or not message.strip():
            self.stats['failed_requests'] += 1
            return False, "请输入有效的消息内容。"
        
        if "错误" in message or "error" in message.lower():
            self.stats['failed_requests'] += 1
            return False, "模拟API错误"
        
        self.stats['successful_requests'] += 1
        self.stats['last_request_time'] = datetime.now()
        
        # 返回模拟响应
        response = self.mock_responses[self.response_index % len(self.mock_responses)]
        self.response_index += 1
        
        return True, response
    
    def is_available(self) -> bool:
        """模拟客户端始终可用"""
        return True
    
    def test_connection(self) -> Tuple[bool, str]:
        """模拟连接测试"""
        return True, "模拟连接测试成功"