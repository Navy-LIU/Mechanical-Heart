# 设计文档

## 概述

AI聊天室是一个基于Python的实时多用户聊天应用，集成了月之暗面AI作为虚拟用户。系统采用WebSocket技术实现实时通信，使用Flask作为Web框架，Flask-SocketIO处理WebSocket连接。当用户通过@AI提及时，系统会调用月之暗面API获取智能回复。

## 架构

### 系统架构图

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端 (HTML/JS) │    │   Flask 应用     │    │  月之暗面 API    │
│                 │    │                 │    │                 │
│  - 聊天界面     │◄──►│  - 路由处理     │◄──►│  - AI 模型服务   │
│  - WebSocket    │    │  - WebSocket    │    │  - OpenAI 兼容   │
│  - 用户交互     │    │  - 消息处理     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   内存存储       │
                       │                 │
                       │  - 用户会话     │
                       │  - 聊天历史     │
                       │  - 在线状态     │
                       └─────────────────┘
```

### 技术栈

- **后端框架**: Flask + Flask-SocketIO
- **实时通信**: WebSocket (Socket.IO)
- **AI集成**: OpenAI Python客户端 + 月之暗面API
- **前端**: HTML5 + JavaScript + Socket.IO客户端
- **样式**: CSS3 (响应式设计)
- **数据存储**: 内存存储 (可扩展为Redis)

## 组件和接口

### 1. Web服务器组件 (app.py)

**职责**: 
- 处理HTTP路由
- 管理WebSocket连接
- 协调消息流转

**主要接口**:
```python
# HTTP路由
@app.route('/')
def index() -> str

# WebSocket事件处理
@socketio.on('connect')
def handle_connect() -> None

@socketio.on('disconnect') 
def handle_disconnect() -> None

@socketio.on('join_room')
def handle_join(data: dict) -> None

@socketio.on('send_message')
def handle_message(data: dict) -> None
```

### 2. 消息处理组件 (message_handler.py)

**职责**:
- 解析和验证消息
- 检测@AI提及
- 管理消息广播

**主要接口**:
```python
class MessageHandler:
    def process_message(self, message: str, user: str) -> dict
    def is_ai_mentioned(self, message: str) -> bool
    def broadcast_message(self, message_data: dict) -> None
    def format_message(self, content: str, user: str, timestamp: datetime) -> dict
```

### 3. AI集成组件 (ai_client.py)

**职责**:
- 管理月之暗面API连接
- 处理AI请求和响应
- 错误处理和重试机制

**主要接口**:
```python
class AIClient:
    def __init__(self, api_key: str, base_url: str)
    def get_ai_response(self, message: str, context: list) -> str
    def handle_api_error(self, error: Exception) -> str
    def format_ai_message(self, response: str) -> dict
```

### 4. 用户管理组件 (user_manager.py)

**职责**:
- 管理用户会话
- 维护在线用户列表
- 处理用户加入/离开

**主要接口**:
```python
class UserManager:
    def add_user(self, session_id: str, username: str) -> bool
    def remove_user(self, session_id: str) -> None
    def get_online_users(self) -> list
    def is_username_taken(self, username: str) -> bool
    def get_user_by_session(self, session_id: str) -> dict
```

### 5. 聊天历史组件 (chat_history.py)

**职责**:
- 存储和检索聊天记录
- 管理消息持久化
- 提供历史消息查询

**主要接口**:
```python
class ChatHistory:
    def add_message(self, message: dict) -> None
    def get_recent_messages(self, limit: int = 50) -> list
    def clear_history(self) -> None
    def get_messages_by_timerange(self, start: datetime, end: datetime) -> list
```

## 数据模型

### 用户模型
```python
@dataclass
class User:
    session_id: str
    username: str
    join_time: datetime
    is_ai: bool = False
    
    def to_dict(self) -> dict
    def is_online(self) -> bool
```

### 消息模型
```python
@dataclass
class Message:
    id: str
    content: str
    username: str
    timestamp: datetime
    message_type: str  # 'user', 'ai', 'system'
    mentions_ai: bool = False
    
    def to_dict(self) -> dict
    def format_for_display(self) -> dict
```

### 聊天室状态模型
```python
@dataclass
class ChatRoomState:
    online_users: dict[str, User]
    message_history: list[Message]
    ai_user: User
    
    def add_user(self, user: User) -> None
    def remove_user(self, session_id: str) -> None
    def add_message(self, message: Message) -> None
```

## 错误处理

### 1. WebSocket连接错误
- 连接断开自动重连机制
- 网络异常时的优雅降级
- 超时处理和状态恢复

### 2. AI API错误处理
- API调用失败时的友好提示
- 请求超时和重试机制
- API配额限制处理

### 3. 用户输入验证
- 消息长度限制
- 用户名格式验证
- XSS攻击防护

### 4. 并发处理
- 用户连接数限制
- 消息频率限制
- 内存使用监控

## 测试策略

### 1. 单元测试
- 消息处理逻辑测试
- AI客户端功能测试
- 用户管理功能测试
- 数据模型验证测试

### 2. 集成测试
- WebSocket连接测试
- AI API集成测试
- 端到端消息流测试

### 3. 性能测试
- 并发用户连接测试
- 消息吞吐量测试
- 内存使用测试

### 4. 用户体验测试
- 前端界面响应性测试
- 实时通信延迟测试
- 移动端适配测试

## 安全考虑

### 1. API密钥安全
- 环境变量存储API密钥
- 服务器端API调用，避免客户端暴露
- 定期轮换API密钥

### 2. 用户输入安全
- 消息内容过滤和转义
- 防止XSS和注入攻击
- 用户名重复检查

### 3. 连接安全
- WebSocket连接验证
- 频率限制防止滥用
- 异常连接监控和断开

## 部署架构

### 开发环境
- 本地Flask开发服务器
- 环境变量配置文件
- 热重载和调试模式

### 生产环境
- Gunicorn + eventlet worker
- Nginx反向代理
- 环境变量或配置管理
- 日志记录和监控