# AI聊天室 URL访问接口文档

## 概述

AI聊天室提供了多种URL访问方式，允许用户和外部系统通过简单的HTTP请求直接发送消息到聊天室，无需传统的WebSocket连接。

## 服务信息

- **服务名称**: AI聊天室 API
- **版本**: 1.0.0
- **基础URL**: `http://localhost:5000` (开发环境)
- **支持格式**: JSON
- **字符编码**: UTF-8

## API 端点详细说明

### 1. 快速发送消息 (GET)

通过URL参数快速发送消息到聊天室。

#### 请求信息
```
GET /quick-send?username={用户名}&message={消息内容}
```

#### 参数说明
| 参数 | 类型 | 必需 | 描述 | 限制 |
|------|------|------|------|------|
| `username` | String | 是 | 用户名 | 最多20个字符 |
| `message` | String | 是 | 消息内容 | 最多1000个字符 |

#### 请求示例
```bash
# 基础用法
curl "http://localhost:5000/quick-send?username=测试用户&message=你好世界"

# URL编码示例
curl "http://localhost:5000/quick-send?username=TestUser&message=Hello%20World"

# 中文支持
curl "http://localhost:5000/quick-send?username=张三&message=这是一条中文消息"
```

#### 响应格式
```json
{
  "success": true,
  "message": "消息发送成功",
  "timestamp": "2025-07-26T11:05:13.675321",
  "user_info": {
    "username": "TestUser (URL)",
    "display_name": "TestUser",
    "session_id": "url_55849639",
    "message_id": "f470d770-9cf5-44f1-a29d-fc6f38091823"
  },
  "ai_response": null
}
```

#### 错误响应示例
```json
{
  "success": false,
  "error": "缺少参数: username 和 message 都是必需的",
  "usage": "/quick-send?username=用户名&message=消息内容"
}
```

### 2. 快速发送消息 (POST)

通过JSON数据快速发送消息到聊天室，支持更多自定义选项。

#### 请求信息
```
POST /quick-send
Content-Type: application/json
```

#### 请求体格式
```json
{
  "username": "用户名",
  "message": "消息内容",
  "display_name": "显示名称" // 可选
}
```

#### 参数说明
| 字段 | 类型 | 必需 | 描述 | 限制 |
|------|------|------|------|------|
| `username` | String | 是 | 用户标识符 | 最多20个字符 |
| `message` | String | 是 | 消息内容 | 最多1000个字符 |
| `display_name` | String | 否 | 显示名称 | 如未提供则使用username |

#### 请求示例
```bash
# 基础POST请求
curl -X POST http://localhost:5000/quick-send \
  -H "Content-Type: application/json" \
  -d '{
    "username": "api_user",
    "message": "Hello from API!"
  }'

# 带显示名称的请求
curl -X POST http://localhost:5000/quick-send \
  -H "Content-Type: application/json" \
  -d '{
    "username": "api_user_001",
    "message": "这是带显示名称的消息",
    "display_name": "API测试用户"
  }'
```

#### 响应格式
```json
{
  "success": true,
  "message": "消息发送成功",
  "timestamp": "2025-07-26T11:05:16.835021",
  "user_info": {
    "username": "PostUser (URL)",
    "display_name": "POST Display",
    "session_id": "url_79dbfd19",
    "message_id": "f83ba69b-e41f-4830-a84d-ec7cacd526bb"
  },
  "ai_response": null
}
```

### 3. 服务状态查询

#### 健康检查
```
GET /health
```

响应示例：
```json
{
  "status": "healthy",
  "service": "ai-chat-room",
  "version": "1.0.0"
}
```

#### MQTT服务状态
```
GET /mqtt/status
```

响应示例：
```json
{
  "success": true,
  "mqtt_status": {
    "is_connected": false,
    "is_running": false,
    "broker_info": "localhost:1883",
    "mqtt_users_count": 0,
    "messages_received": 0,
    "messages_sent": 0,
    "connect_time": null,
    "last_message_time": null,
    "active_topics": [
      "chatroom/messages/in",
      "chatroom/messages/out",
      "chatroom/users/join",
      "chatroom/users/leave",
      "chatroom/system"
    ],
    "mqtt_users": []
  },
  "timestamp": "2025-07-26T11:04:58.768032"
}
```

### 4. API文档查询
```
GET /api/docs
```

返回完整的API文档信息，包括所有端点的详细说明。

## 用户标识系统

URL访问的用户会被特殊标记：
- **用户名格式**: `{原用户名} (URL)`
- **会话ID格式**: `url_{8位随机字符串}`
- **IP识别**: 系统会根据请求IP自动分配用户ID
- **显示名称**: 可通过POST请求自定义

## 与聊天室系统集成

### 消息广播
通过URL发送的消息会：
1. 立即广播给所有连接的WebSocket客户端
2. 触发AI自动回复（如果配置）
3. 转发到MQTT系统（如果启用）
4. 记录到聊天历史数据库

### 用户管理
- URL用户不受30用户限制约束
- 每次请求创建临时会话
- 不会出现在在线用户列表中
- 消息会正常显示给其他用户

## 使用场景

### 1. IoT设备集成
```bash
# 温度传感器报告
curl "http://chatroom.example.com/quick-send?username=TempSensor&message=当前温度：25°C"
```

### 2. 系统通知
```bash
# 系统状态通知
curl -X POST http://chatroom.example.com/quick-send \
  -H "Content-Type: application/json" \
  -d '{
    "username": "system_monitor",
    "message": "服务器重启完成",
    "display_name": "系统监控"
  }'
```

### 3. 外部应用集成
```python
import requests

def send_message_to_chat(username, message, display_name=None):
    url = "http://localhost:5000/quick-send"
    data = {
        "username": username,
        "message": message
    }
    if display_name:
        data["display_name"] = display_name
    
    response = requests.post(url, json=data)
    return response.json()

# 使用示例
result = send_message_to_chat("python_script", "Python脚本执行完成", "自动化脚本")
print(result)
```

### 4. Webhook集成
```bash
# 可以作为webhook接收器使用
curl -X POST http://localhost:5000/quick-send \
  -H "Content-Type: application/json" \
  -d '{
    "username": "github_webhook",
    "message": "代码已推送到主分支",
    "display_name": "GitHub通知"
  }'
```

## 错误处理

### 常见错误代码

| HTTP状态码 | 错误类型 | 描述 |
|------------|----------|------|
| 400 | 参数错误 | 缺少必需参数或参数格式不正确 |
| 500 | 服务器错误 | 内部处理异常 |

### 错误响应格式
```json
{
  "success": false,
  "error": "错误描述信息"
}
```

### 参数验证规则

1. **用户名验证**
   - 不能为空
   - 长度不超过20个字符
   - 会自动添加"(URL)"后缀

2. **消息内容验证**
   - 不能为空
   - 长度不超过1000个字符
   - 支持中文和特殊字符

3. **URL编码处理**
   - GET请求参数会自动URL解码
   - 支持中文字符的正确编码

## 安全考虑

### 访问控制
- 当前版本无需身份验证
- 建议在生产环境中添加API密钥验证
- 可通过防火墙限制访问IP

### 速率限制
- 目前无速率限制
- 建议根据需要添加请求频率控制

### 内容过滤
- 消息内容长度限制
- 建议添加敏感词过滤
- 可添加内容审核机制

## 高级特性

### MQTT集成
URL发送的消息会自动转发到MQTT系统，支持：
- 消息双向同步
- 多客户端实时通信
- IoT设备无缝集成

详细MQTT配置请参考下一节。

## 故障排除

### 常见问题

1. **消息发送失败**
   - 检查参数格式是否正确
   - 验证服务器是否正常运行
   - 查看服务器日志获取详细错误信息

2. **中文乱码**
   - 确保使用UTF-8编码
   - GET请求中文参数需要URL编码
   - POST请求设置正确的Content-Type头

3. **连接超时**
   - 检查网络连接
   - 验证服务器地址和端口
   - 确认防火墙设置

### 调试技巧

```bash
# 启用详细输出
curl -v "http://localhost:5000/quick-send?username=debug&message=test"

# 检查服务状态
curl http://localhost:5000/health

# 查看完整API文档
curl http://localhost:5000/api/docs | jq
```

## 更新日志

### v1.0.0 (当前版本)
- ✅ 实现URL直接访问功能
- ✅ 支持GET和POST两种请求方式
- ✅ 完整的错误处理机制
- ✅ 用户标识和会话管理
- ✅ MQTT服务集成
- ✅ 中文字符支持
- ✅ 自动消息广播

---

*文档更新时间: 2025年7月26日*
*如有问题或建议，请联系开发团队*