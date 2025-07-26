# 云台HTTP控制API使用指南

## 概述

本指南介绍如何使用新增的云台HTTP控制API，实现通过HTTP请求直接控制云台设备，无需通过聊天室界面。

## API端点

### 1. 云台控制API

**端点**: `POST /api/gimbal/control`  
**描述**: 直接控制云台移动到指定位置

#### 请求参数

```json
{
  "x": 2500,          // 水平角度 (必需，范围: 1024-3048)
  "y": 2000,          // 垂直角度 (必需，范围: 1850-2400)
  "username": "用户名" // 操作用户 (可选，默认: "API_User")
}
```

#### 响应示例

成功响应：
```json
{
  "success": true,
  "message": "云台控制指令已发送: X=2500, Y=2000",
  "control_data": {
    "x": 2500,
    "y": 2000,
    "username": "API_User",
    "timestamp": "2025-07-26T14:58:10.015783"
  }
}
```

错误响应：
```json
{
  "success": false,
  "error": "参数 x 超出范围: 5000，应在1024-3048之间"
}
```

#### 使用示例

```bash
# 基本控制指令
curl -X POST -H "Content-Type: application/json" \
     -d '{"x": 2500, "y": 2000}' \
     http://localhost:5000/api/gimbal/control

# 指定用户名的控制指令
curl -X POST -H "Content-Type: application/json" \
     -d '{"x": 2800, "y": 2200, "username": "管理员"}' \
     http://localhost:5000/api/gimbal/control
```

### 2. 云台状态查询API

**端点**: `GET /api/gimbal/status`  
**描述**: 获取所有已连接云台设备的实时状态信息

#### 响应示例

```json
{
  "success": true,
  "message": "云台状态获取成功",
  "gimbals": [
    {
      "client_id": "gimbal_1753556272",
      "username": "云台",
      "device_type": "gimbal",
      "status": "online",
      "last_seen": "Sat, 26 Jul 2025 14:58:52 GMT",
      "register_time": "Sat, 26 Jul 2025 14:57:52 GMT",
      "model": "Simulated Gimbal v1.0",
      "current_position": {
        "x": 1500,
        "y": 2300
      },
      "position_limits": {
        "x": {"min": 1024, "max": 3048},
        "y": {"min": 1850, "max": 2400}
      },
      "capabilities": ["angle_control", "position_feedback"],
      "stats": {
        "connect_time": "2025-07-26T14:54:09.337671",
        "commands_received": 2,
        "commands_executed": 2,
        "position_changes": 2,
        "last_command_time": "2025-07-26T14:58:50.848802"
      }
    }
  ],
  "total_count": 1,
  "timestamp": "2025-07-26T14:59:00.000000"
}
```

#### 使用示例

```bash
# 获取云台状态
curl http://localhost:5000/api/gimbal/status
```

### 3. 云台设备列表API

**端点**: `GET /api/gimbal/list`  
**描述**: 获取所有已注册的云台设备信息

#### 响应示例

```json
{
  "success": true,
  "message": "云台设备列表获取成功",
  "devices": [
    {
      "client_id": "gimbal_1753556272",
      "username": "云台",
      "device_type": "gimbal",
      "is_online": true,
      "register_time": "Sat, 26 Jul 2025 14:57:52 GMT",
      "last_seen": "Sat, 26 Jul 2025 14:58:52 GMT",
      "model": "Simulated Gimbal v1.0",
      "position_limits": {
        "x": {"min": 1024, "max": 3048},
        "y": {"min": 1850, "max": 2400}
      },
      "capabilities": ["angle_control", "position_feedback"],
      "current_position": {"x": 1500, "y": 2300}
    }
  ],
  "total_count": 1,
  "timestamp": "2025-07-26T14:59:00.000000"
}
```

#### 使用示例

```bash
# 获取设备列表
curl http://localhost:5000/api/gimbal/list
```

## 错误处理

### 常见错误类型

1. **参数验证错误**
   - 缺少必需参数: `"缺少必需参数: x 和 y"`
   - 参数类型错误: `"参数 x 和 y 必须是整数"`
   - 参数超出范围: `"参数 x 超出范围: 5000，应在1024-3048之间"`

2. **服务状态错误**
   - MQTT服务不可用: `"MQTT服务不可用"`
   - 发送指令失败: `"发送云台控制指令失败"`

3. **HTTP状态码**
   - `200`: 请求成功
   - `400`: 请求参数错误
   - `500`: 服务器内部错误
   - `503`: 服务不可用（MQTT离线）

## 集成示例

### Python示例

```python
import requests
import json

# 云台控制函数
def control_gimbal(x, y, username="Python_Client"):
    url = "http://localhost:5000/api/gimbal/control"
    data = {
        "x": x,
        "y": y,
        "username": username
    }
    
    try:
        response = requests.post(url, json=data)
        result = response.json()
        
        if result['success']:
            print(f"云台控制成功: X={x}, Y={y}")
            return True
        else:
            print(f"云台控制失败: {result['error']}")
            return False
            
    except Exception as e:
        print(f"请求异常: {e}")
        return False

# 获取云台状态函数
def get_gimbal_status():
    url = "http://localhost:5000/api/gimbal/status"
    
    try:
        response = requests.get(url)
        result = response.json()
        
        if result['success']:
            print(f"在线云台数量: {result['total_count']}")
            for gimbal in result['gimbals']:
                pos = gimbal['current_position']
                print(f"云台 {gimbal['client_id']}: 位置 ({pos['x']}, {pos['y']})")
        else:
            print(f"获取状态失败: {result['error']}")
            
    except Exception as e:
        print(f"请求异常: {e}")

# 使用示例
if __name__ == "__main__":
    # 控制云台
    control_gimbal(2000, 2100, "Python测试")
    
    # 等待一段时间让云台移动完成
    import time
    time.sleep(2)
    
    # 查看状态
    get_gimbal_status()
```

### JavaScript示例

```javascript
// 云台控制函数
async function controlGimbal(x, y, username = "JS_Client") {
    const url = "http://localhost:5000/api/gimbal/control";
    const data = { x, y, username };
    
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log(`云台控制成功: X=${x}, Y=${y}`);
            return true;
        } else {
            console.log(`云台控制失败: ${result.error}`);
            return false;
        }
    } catch (error) {
        console.log(`请求异常: ${error}`);
        return false;
    }
}

// 获取云台状态函数
async function getGimbalStatus() {
    const url = "http://localhost:5000/api/gimbal/status";
    
    try {
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.success) {
            console.log(`在线云台数量: ${result.total_count}`);
            result.gimbals.forEach(gimbal => {
                const pos = gimbal.current_position;
                console.log(`云台 ${gimbal.client_id}: 位置 (${pos.x}, ${pos.y})`);
            });
        } else {
            console.log(`获取状态失败: ${result.error}`);
        }
    } catch (error) {
        console.log(`请求异常: ${error}`);
    }
}

// 使用示例
(async () => {
    // 控制云台
    await controlGimbal(2500, 2200, "JS测试");
    
    // 等待一段时间让云台移动完成
    setTimeout(async () => {
        // 查看状态
        await getGimbalStatus();
    }, 2000);
})();
```

## 注意事项

1. **参数范围**: 
   - X轴范围: 1024-3048
   - Y轴范围: 1850-2400

2. **MQTT依赖**: 
   - API功能依赖MQTT服务，确保MQTT代理正常运行
   - 云台设备必须先连接到MQTT代理才能接收控制指令

3. **实时性**: 
   - 控制指令立即发送，但云台移动需要时间
   - 建议在控制后适当等待再查询状态

4. **并发控制**: 
   - 多个控制指令会按顺序执行
   - 建议避免频繁发送控制指令

5. **错误恢复**: 
   - 如果云台离线，控制指令会失败
   - 可通过状态查询API检查设备在线状态

## 完整API文档

所有API文档可通过以下端点获取：

```bash
curl http://localhost:5000/api/docs
```

这将返回完整的API文档，包括所有端点的详细说明。