# 修正版MQTT云台管理器

这是按照您要求修正的MQTT云台管理程序，严格使用指定的主题名称：

- `camera/manager/set_mode` - **服务器调整云台运行模式** (服务器 → 云台)
- `camera/tracking/set_mode` - **云台发布自身运行模式** (云台 → 服务器)

## 主题功能说明

### 1. `camera/manager/set_mode` (服务器 → 云台)

**此主题接收两类指令：**

#### A. 模式切换指令
```json
{"mode": "auto"}     // 切换到自动追踪模式
{"mode": "manual"}   // 切换到手动控制模式
```

#### B. 云台控制指令

##### 移动控制
```json
{
  "command": "move",
  "pan": 45,        // 水平角度 (-180 到 180)
  "tilt": -30,      // 俯仰角度 (-90 到 90)  
  "speed": 1.5      // 移动速度 (可选，默认1.0)
}
```

##### 缩放控制
```json
{
  "command": "zoom",
  "zoom": 2.0       // 缩放倍数
}
```

##### 预设位置
```json
{
  "command": "preset",
  "preset_id": 1    // 预设位置ID (1-4)
}
```

预设位置定义：
- 1: 正前方 (pan: 0°, tilt: 0°)
- 2: 右前方俯视 (pan: 90°, tilt: -30°)
- 3: 左前方俯视 (pan: -90°, tilt: -30°)
- 4: 正后方 (pan: 180°, tilt: 0°)

##### 校准
```json
{
  "command": "calibrate"
}
```

##### 重置
```json
{
  "command": "reset"
}
```

### 2. `camera/tracking/set_mode` (云台 → 服务器)

**云台每秒自动发布运行状态：**

```json
{
  "mode": "auto",           // 当前运行模式: idle/auto/manual
  "gimbal": {
    "pan": 45.0,            // 当前水平角度
    "tilt": -30.0,          // 当前俯仰角度
    "roll": 0.0,            // 当前翻滚角度
    "zoom": 2.0,            // 当前缩放倍数
    "mode": "tracking",     // 云台模式: idle/tracking/manual_control
    "online": true,         // 是否在线
    "battery": 95           // 电池电量百分比
  },
  "timestamp": 1640995200000  // 时间戳(毫秒)
}
```

## 程序架构

```
MQTT Broker (192.168.137.1:1883)
    │
    ├── camera/manager/set_mode    (服务器 → 云台) 
    │   ├── 模式切换指令 {"mode": "auto/manual"}
    │   └── 云台控制指令 {"command": "move/zoom/preset/calibrate/reset", ...}
    │
    └── camera/tracking/set_mode   (云台 → 服务器)
        └── 运行状态发布 {"mode": "...", "gimbal": {...}, "timestamp": ...}
```

## 文件说明

- `corrected_mqtt_manager.py` - 修正版主程序
- `corrected_test_script.py` - 修正版测试脚本
- `CORRECTED_README.md` - 本说明文档

## 使用方法

### 1. 运行主程序
```bash
python3 corrected_mqtt_manager.py
```

### 2. 运行测试脚本（在另一个终端）
```bash
python3 corrected_test_script.py
```

## 主要修正点

1. **严格按照指定主题命名**
   - `camera/manager/set_mode` 作为唯一的控制指令接收主题
   - `camera/tracking/set_mode` 作为状态发布主题

2. **统一的指令处理**
   - 所有控制指令（模式切换和云台控制）都通过 `camera/manager/set_mode` 发送
   - 程序自动识别指令类型并执行相应操作

3. **完整的状态反馈**
   - 通过 `camera/tracking/set_mode` 发布完整的运行状态信息
   - 包含运行模式和详细的云台状态

4. **向后兼容性**
   - 保持原有的C++自动进程和Python手动进程控制逻辑
   - 内部仍使用原有的进程间通信机制

## 测试示例

### 模式切换
```bash
# 切换到手动模式
mosquitto_pub -h 192.168.137.1 -t "camera/manager/set_mode" -m '{"mode":"manual"}'

# 切换到自动模式
mosquitto_pub -h 192.168.137.1 -t "camera/manager/set_mode" -m '{"mode":"auto"}'
```

### 云台控制
```bash
# 移动云台
mosquitto_pub -h 192.168.137.1 -t "camera/manager/set_mode" -m '{"command":"move","pan":45,"tilt":-30,"speed":1.5}'

# 缩放控制
mosquitto_pub -h 192.168.137.1 -t "camera/manager/set_mode" -m '{"command":"zoom","zoom":2.0}'

# 预设位置
mosquitto_pub -h 192.168.137.1 -t "camera/manager/set_mode" -m '{"command":"preset","preset_id":2}'
```

### 状态监控
```bash
# 监控云台状态
mosquitto_sub -h 192.168.137.1 -t "camera/tracking/set_mode"
```

## 注意事项

1. **主题严格性** - 程序严格按照您指定的主题名称实现，不添加额外主题
2. **指令格式** - 所有指令必须是有效的JSON格式
3. **状态实时性** - 云台状态每秒更新一次，确保实时性
4. **错误处理** - 包含完善的异常处理和日志输出