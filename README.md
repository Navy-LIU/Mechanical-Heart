# AI聊天室

一个基于Python Flask的实时多用户聊天室，集成月之暗面AI作为虚拟用户。

## 功能特性

- 🚀 实时多用户聊天
- 🤖 AI虚拟用户集成（月之暗面API）
- 💬 @AI触发智能回复
- 👥 在线用户列表
- 📱 响应式设计
- 🔒 安全的API密钥管理
- 🎥 云台设备控制集成
- 📡 MQTT通信支持
- 🔌 HTTP API接口

## 技术栈

- **后端**: Flask + Flask-SocketIO
- **前端**: HTML5 + CSS3 + JavaScript
- **实时通信**: WebSocket (Socket.IO)
- **AI集成**: 月之暗面API (OpenAI兼容)
- **MQTT**: 支持MQTT通信协议
- **设备控制**: 云台设备集成

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
4. 使用 `@云台 Ang_x=2500 Ang_Y=2000` 命令控制云台设备
5. 查看右侧用户列表了解在线用户

## 云台控制功能

本项目支持通过MQTT协议控制云台设备，提供两种控制方式：

### 1. 聊天室控制

在聊天室中使用以下命令格式：
```
@云台 Ang_x=2500 Ang_Y=2000
```

### 2. HTTP API控制

直接通过HTTP API接口控制：

```bash
# 云台控制
curl -X POST -H "Content-Type: application/json" \
     -d '{"x": 2500, "y": 2000, "username": "用户名"}' \
     http://localhost:5000/api/gimbal/control

# 查询状态
curl http://localhost:5000/api/gimbal/status

# 设备列表
curl http://localhost:5000/api/gimbal/list
```

### 云台设备启动

```bash
# 启动云台设备模拟器
python3 gimbal_device_simulator.py --host 127.0.0.1 --port 1883
```

详细使用说明请查看：[**云台HTTP控制API使用指南**](云台HTTP控制API使用指南.md)

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