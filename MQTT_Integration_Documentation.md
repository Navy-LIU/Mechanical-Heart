# AI聊天室 MQTT集成文档

## 概述

AI聊天室支持完整的MQTT集成，允许IoT设备、移动应用和其他系统通过MQTT协议与聊天室进行实时通信。MQTT集成提供了双向消息同步，支持用户管理和系统通知。

## MQTT服务配置

### 环境变量配置

在 `.env` 文件中配置MQTT服务：

```bash
# MQTT配置
MQTT_ENABLE=true              # 启用MQTT服务
MQTT_BROKER=localhost         # MQTT代理服务器地址
MQTT_PORT=1883               # MQTT代理服务器端口
```

### 支持的MQTT代理

- **Mosquitto** (推荐)
- **Eclipse Paho**
- **HiveMQ**
- **AWS IoT Core**
- **Azure IoT Hub**

## MQTT主题架构

### 主题列表

| 主题 | 方向 | 描述 | 消息格式 |
|------|------|------|----------|
| `chatroom/messages/in` | 发布 → 聊天室 | 发送消息到聊天室 | JSON |
| `chatroom/messages/out` | 聊天室 → 订阅 | 从聊天室接收消息 | JSON |
| `chatroom/users/join` | 发布 → 聊天室 | 用户加入通知 | JSON |
| `chatroom/users/leave` | 发布 → 聊天室 | 用户离开通知 | JSON |
| `chatroom/system` | 聊天室 → 订阅 | 系统消息和通知 | JSON |

### 主题详细说明

#### 1. 消息发送 (`chatroom/messages/in`)

向聊天室发送消息。

**消息格式:**
```json
{
  "client_id": "mqtt_client_001",
  "username": "MQTT用户",
  "message": "Hello from MQTT!"
}
```

**字段说明:**
- `client_id`: MQTT客户端唯一标识符
- `username`: 用户显示名称
- `message`: 消息内容（必填，不能为空）

#### 2. 消息接收 (`chatroom/messages/out`)

订阅此主题可接收聊天室中的所有消息。

**用户消息格式:**
```json
{
  "type": "user_message",
  "username": "张三",
  "content": "你好世界",
  "timestamp": "2025-07-26T11:05:13.675321",
  "message_id": "f470d770-9cf5-44f1-a29d-fc6f38091823"
}
```

**AI回复格式:**
```json
{
  "type": "ai_response",
  "username": "智能助手",
  "content": "您好！有什么可以帮助您的吗？",
  "timestamp": "2025-07-26T11:05:14.123456",
  "message_id": "ai-response-456"
}
```

#### 3. 用户加入 (`chatroom/users/join`)

通知系统用户加入聊天室。

**消息格式:**
```json
{
  "client_id": "mqtt_client_001",
  "username": "新用户"
}
```

#### 4. 用户离开 (`chatroom/users/leave`)

通知系统用户离开聊天室。

**消息格式:**
```json
{
  "client_id": "mqtt_client_001"
}
```

#### 5. 系统消息 (`chatroom/system`)

系统通知和状态更新。

**消息格式:**
```json
{
  "type": "system_message",
  "message": "MQTT服务已连接",
  "timestamp": "2025-07-26T11:05:13.675321"
}
```

## 客户端实现示例

### Python客户端 (paho-mqtt)

```python
import paho.mqtt.client as mqtt
import json
from datetime import datetime

class ChatRoomMQTTClient:
    def __init__(self, client_id, username, broker_host="localhost", broker_port=1883):
        self.client_id = client_id
        self.username = username
        self.broker_host = broker_host
        self.broker_port = broker_port
        
        # 创建MQTT客户端
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ 连接成功: {self.broker_host}:{self.broker_port}")
            
            # 订阅输出主题
            client.subscribe("chatroom/messages/out")
            client.subscribe("chatroom/system")
            
            # 发送用户加入消息
            self.join_chat()
        else:
            print(f"❌ 连接失败，错误代码: {rc}")
    
    def on_message(self, client, userdata, message):
        topic = message.topic
        payload = message.payload.decode('utf-8')
        
        try:
            msg_data = json.loads(payload)
            print(f"📨 [{topic}] {json.dumps(msg_data, ensure_ascii=False, indent=2)}")
        except json.JSONDecodeError:
            print(f"📨 [{topic}] {payload}")
    
    def connect(self):
        """连接到MQTT代理"""
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"❌ 连接异常: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self.leave_chat()
        self.client.loop_stop()
        self.client.disconnect()
    
    def join_chat(self):
        """加入聊天室"""
        join_msg = {
            "client_id": self.client_id,
            "username": self.username
        }
        self.client.publish("chatroom/users/join", json.dumps(join_msg, ensure_ascii=False))
        print(f"👋 {self.username} 已加入聊天室")
    
    def leave_chat(self):
        """离开聊天室"""
        leave_msg = {
            "client_id": self.client_id
        }
        self.client.publish("chatroom/users/leave", json.dumps(leave_msg, ensure_ascii=False))
        print(f"👋 {self.username} 已离开聊天室")
    
    def send_message(self, message):
        """发送消息"""
        msg_data = {
            "client_id": self.client_id,
            "username": self.username,
            "message": message
        }
        self.client.publish("chatroom/messages/in", json.dumps(msg_data, ensure_ascii=False))
        print(f"📤 发送消息: {message}")

# 使用示例
if __name__ == "__main__":
    client = ChatRoomMQTTClient("python_client_001", "Python用户")
    
    if client.connect():
        try:
            # 发送一些测试消息
            client.send_message("Hello from Python MQTT client!")
            client.send_message("这是中文消息测试")
            
            # 保持连接，接收消息
            input("按回车键断开连接...")
        finally:
            client.disconnect()
```

### Node.js客户端

```javascript
const mqtt = require('mqtt');

class ChatRoomMQTTClient {
    constructor(clientId, username, brokerHost = 'localhost', brokerPort = 1883) {
        this.clientId = clientId;
        this.username = username;
        this.brokerUrl = `mqtt://${brokerHost}:${brokerPort}`;
        
        // 创建MQTT客户端
        this.client = mqtt.connect(this.brokerUrl);
        
        // 设置事件监听器
        this.client.on('connect', this.onConnect.bind(this));
        this.client.on('message', this.onMessage.bind(this));
        this.client.on('error', this.onError.bind(this));
    }
    
    onConnect() {
        console.log(`✅ 连接成功: ${this.brokerUrl}`);
        
        // 订阅输出主题
        this.client.subscribe(['chatroom/messages/out', 'chatroom/system']);
        
        // 发送用户加入消息
        this.joinChat();
    }
    
    onMessage(topic, message) {
        const payload = message.toString();
        
        try {
            const msgData = JSON.parse(payload);
            console.log(`📨 [${topic}]`, JSON.stringify(msgData, null, 2));
        } catch (e) {
            console.log(`📨 [${topic}] ${payload}`);
        }
    }
    
    onError(error) {
        console.error(`❌ MQTT错误: ${error}`);
    }
    
    joinChat() {
        const joinMsg = {
            client_id: this.clientId,
            username: this.username
        };
        this.client.publish('chatroom/users/join', JSON.stringify(joinMsg));
        console.log(`👋 ${this.username} 已加入聊天室`);
    }
    
    leaveChat() {
        const leaveMsg = {
            client_id: this.clientId
        };
        this.client.publish('chatroom/users/leave', JSON.stringify(leaveMsg));
        console.log(`👋 ${this.username} 已离开聊天室`);
    }
    
    sendMessage(message) {
        const msgData = {
            client_id: this.clientId,
            username: this.username,
            message: message
        };
        this.client.publish('chatroom/messages/in', JSON.stringify(msgData));
        console.log(`📤 发送消息: ${message}`);
    }
    
    disconnect() {
        this.leaveChat();
        this.client.end();
        console.log('🔌 连接已断开');
    }
}

// 使用示例
const client = new ChatRoomMQTTClient('nodejs_client_001', 'Node.js用户');

// 发送测试消息
setTimeout(() => {
    client.sendMessage('Hello from Node.js MQTT client!');
    client.sendMessage('这是来自Node.js的中文消息');
}, 2000);

// 优雅退出
process.on('SIGINT', () => {
    console.log('\\n正在断开连接...');
    client.disconnect();
    process.exit(0);
});
```

## IoT设备集成示例

### Arduino/ESP32

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

const char* ssid = "your_wifi_ssid";
const char* password = "your_wifi_password";
const char* mqtt_server = "your_mqtt_broker_ip";
const int mqtt_port = 1883;

WiFiClient espClient;
PubSubClient client(espClient);

const char* device_id = "esp32_sensor_001";
const char* device_name = "温度传感器";

void setup() {
    Serial.begin(115200);
    
    // 连接WiFi
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("WiFi connected");
    
    // 配置MQTT
    client.setServer(mqtt_server, mqtt_port);
    client.setCallback(onMqttMessage);
}

void loop() {
    if (!client.connected()) {
        reconnectMqtt();
    }
    client.loop();
    
    // 每30秒发送一次温度数据
    static unsigned long lastMsg = 0;
    unsigned long now = millis();
    if (now - lastMsg > 30000) {
        lastMsg = now;
        sendTemperature();
    }
}

void reconnectMqtt() {
    while (!client.connected()) {
        Serial.print("Attempting MQTT connection...");
        
        if (client.connect(device_id)) {
            Serial.println("connected");
            
            // 订阅消息
            client.subscribe("chatroom/messages/out");
            client.subscribe("chatroom/system");
            
            // 发送加入消息
            joinChat();
        } else {
            Serial.print("failed, rc=");
            Serial.print(client.state());
            Serial.println(" try again in 5 seconds");
            delay(5000);
        }
    }
}

void joinChat() {
    StaticJsonDocument<200> doc;
    doc["client_id"] = device_id;
    doc["username"] = device_name;
    
    String message;
    serializeJson(doc, message);
    
    client.publish("chatroom/users/join", message.c_str());
    Serial.println("Joined chat room");
}

void sendTemperature() {
    // 模拟温度读取
    float temperature = 20.0 + random(0, 100) / 10.0;
    
    StaticJsonDocument<300> doc;
    doc["client_id"] = device_id;
    doc["username"] = device_name;
    doc["message"] = String("当前温度: ") + String(temperature, 1) + "°C";
    
    String message;
    serializeJson(doc, message);
    
    client.publish("chatroom/messages/in", message.c_str());
    
    Serial.print("Temperature sent: ");
    Serial.println(temperature);
}

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
    String message;
    for (int i = 0; i < length; i++) {
        message += (char)payload[i];
    }
    
    Serial.print("Message received [");
    Serial.print(topic);
    Serial.print("]: ");
    Serial.println(message);
}
```

## 服务状态monitoring

### MQTT服务状态API

查询MQTT服务状态:
```bash
curl http://localhost:5000/mqtt/status
```

响应示例:
```json
{
  "success": true,
  "mqtt_status": {
    "is_connected": true,
    "is_running": true,
    "broker_info": "localhost:1883",
    "mqtt_users_count": 3,
    "messages_received": 125,
    "messages_sent": 89,
    "connect_time": "2025-07-26T10:30:15.123456",
    "last_message_time": "2025-07-26T11:05:13.675321",
    "active_topics": [
      "chatroom/messages/in",
      "chatroom/messages/out",
      "chatroom/users/join",
      "chatroom/users/leave",
      "chatroom/system"
    ],
    "mqtt_users": [
      {
        "client_id": "python_client_001",
        "username": "Python用户",
        "join_time": "2025-07-26T10:30:15.123456",
        "message_count": 5
      }
    ]
  },
  "timestamp": "2025-07-26T11:05:13.675321"
}
```

## 故障排除

### 常见问题

#### 1. 连接失败
```
error: [Errno 111] Connection refused
```

**解决方案:**
- 确保MQTT代理服务器正在运行
- 检查代理地址和端口配置
- 验证网络连接和防火墙设置

#### 2. 消息未接收
**可能原因:**
- 主题订阅错误
- 消息格式不正确
- 客户端连接断开

**调试步骤:**
```bash
# 使用mosquitto客户端测试
mosquitto_sub -h localhost -p 1883 -t "chatroom/messages/out" -v

# 发送测试消息
mosquitto_pub -h localhost -p 1883 -t "chatroom/messages/in" \
  -m '{"client_id":"test","username":"测试","message":"hello"}'
```

#### 3. 中文字符问题
**解决方案:**
- 确保所有客户端使用UTF-8编码
- JSON序列化时设置`ensure_ascii=False`
- 检查MQTT代理的字符编码支持

### 性能优化

#### 连接池管理
```python
from paho.mqtt.client import Client
import threading

class MQTTConnectionPool:
    def __init__(self, max_connections=10):
        self.pool = []
        self.max_connections = max_connections
        self.lock = threading.Lock()
    
    def get_client(self):
        with self.lock:
            if self.pool:
                return self.pool.pop()
        return self.create_client()
    
    def return_client(self, client):
        with self.lock:
            if len(self.pool) < self.max_connections:
                self.pool.append(client)
            else:
                client.disconnect()
```

#### QoS设置
```python
# QoS级别选择
# 0: 最多一次投递（不可靠）
# 1: 至少一次投递（默认，推荐）
# 2: 仅一次投递（最可靠，性能较低）

client.publish("chatroom/messages/in", message, qos=1)
```

## 安全考虑

### 认证配置
```python
# 用户名/密码认证
client.username_pw_set("mqtt_username", "mqtt_password")

# TLS/SSL加密
import ssl
context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
client.tls_set_context(context)
```

### 访问控制列表 (ACL)
```
# mosquitto ACL配置示例
user mqtt_user_001
topic readwrite chatroom/messages/in
topic read chatroom/messages/out
topic read chatroom/system
```

## 扩展功能

### 消息持久化
```python
# 设置消息保留
client.publish("chatroom/system", message, retain=True)
```

### 离线消息
```python
# 设置客户端会话持久化
client = mqtt.Client(clean_session=False)
```

### 消息路由
可以通过配置不同的主题前缀来支持多个聊天室:
```
chatroom/room1/messages/in
chatroom/room1/messages/out
chatroom/room2/messages/in
chatroom/room2/messages/out
```

---

*文档更新时间: 2025年7月26日*
*如需技术支持，请联系开发团队*