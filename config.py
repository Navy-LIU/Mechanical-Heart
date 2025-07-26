"""
应用配置管理
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """基础配置类"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # 月之暗面API配置
    MOONSHOT_API_KEY = os.getenv('MOONSHOT_API_KEY')
    MOONSHOT_BASE_URL = os.getenv('MOONSHOT_BASE_URL', 'https://api.moonshot.ai/v1')
    
    # 聊天室配置
    MAX_USERS = int(os.getenv('MAX_USERS', 100))
    MAX_MESSAGE_LENGTH = int(os.getenv('MAX_MESSAGE_LENGTH', 1000))
    MESSAGE_HISTORY_LIMIT = int(os.getenv('MESSAGE_HISTORY_LIMIT', 100))
    
    @classmethod
    def validate_config(cls):
        """验证必要的配置项"""
        if not cls.MOONSHOT_API_KEY:
            raise ValueError("MOONSHOT_API_KEY环境变量未设置")
        
        if not cls.MOONSHOT_BASE_URL:
            raise ValueError("MOONSHOT_BASE_URL环境变量未设置")

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = True
    TESTING = True
    # 测试时使用模拟API
    MOONSHOT_API_KEY = 'test-api-key'

# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}