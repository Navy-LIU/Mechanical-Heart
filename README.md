# AI聊天室

一个基于Python Flask的实时多用户聊天室，集成月之暗面AI作为虚拟用户。

## 功能特性

- 🚀 实时多用户聊天
- 🤖 AI虚拟用户集成（月之暗面API）
- 💬 @AI触发智能回复
- 👥 在线用户列表
- 📱 响应式设计
- 🔒 安全的API密钥管理

## 技术栈

- **后端**: Flask + Flask-SocketIO
- **前端**: HTML5 + CSS3 + JavaScript
- **实时通信**: WebSocket (Socket.IO)
- **AI集成**: 月之暗面API (OpenAI兼容)

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的月之暗面API密钥：

```env
MOONSHOT_API_KEY=sk-your-api-key-here
```

### 3. 运行应用

```bash
python app.py
```

访问 http://localhost:5000 开始聊天！

## 使用说明

1. 打开网站，输入昵称加入聊天室
2. 在聊天框中输入消息与其他用户交流
3. 使用 `@AI` 来与AI助手对话
4. 查看右侧用户列表了解在线用户

## 项目结构

```
ai-chat-website/
├── app.py              # 主应用入口
├── config.py           # 配置管理
├── requirements.txt    # 依赖包
├── .env.example       # 环境变量示例
├── models/            # 数据模型
├── services/          # 业务服务
├── templates/         # HTML模板
├── static/           # 静态资源
│   ├── css/         # 样式文件
│   └── js/          # JavaScript文件
└── tests/            # 测试文件
```

## 开发指南

### 运行测试

```bash
pytest
```

### 生产环境部署

使用Gunicorn运行：

```bash
gunicorn --worker-class eventlet -w 1 app:app
```

## 许可证

MIT License