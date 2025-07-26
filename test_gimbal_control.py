#!/usr/bin/env python3
"""
测试脚本：演示如何使用新增的云台控制和状态监控功能
"""

import paho.mqtt.client as mqtt
import json
import time

# MQTT配置
MQTT_BROKER_HOST = "192.168.137.1"
MQTT_BROKER_PORT = 1883

# MQTT主题
GIMBAL_CONTROL_TOPIC = "camera/gimbal/control"
GIMBAL_STATUS_TOPIC = "camera/gimbal/status"
MANAGER_TOPIC = "camera/manager/set_mode"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("测试客户端已连接到MQTT服务器")
        # 订阅云台状态主题以监控状态变化
        client.subscribe(GIMBAL_STATUS_TOPIC)
        print(f"已订阅云台状态主题: {GIMBAL_STATUS_TOPIC}")
    else:
        print(f"连接失败，返回码: {rc}")

def on_message(client, userdata, msg):
    """处理收到的云台状态消息"""
    if msg.topic == GIMBAL_STATUS_TOPIC:
        try:
            status = json.loads(msg.payload.decode('utf-8'))
            print(f"\n[云台状态更新]: {json.dumps(status, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"解析状态消息失败: {e}")

def send_gimbal_control_command(client, command):
    """发送云台控制指令"""
    try:
        command_json = json.dumps(command, ensure_ascii=False)
        print(f"\n发送云台控制指令: {command_json}")
        client.publish(GIMBAL_CONTROL_TOPIC, command_json, qos=1)
    except Exception as e:
        print(f"发送控制指令失败: {e}")

def send_mode_change_command(client, mode):
    """发送模式切换指令"""
    try:
        command = {"mode": mode}
        command_json = json.dumps(command)
        print(f"\n发送模式切换指令: {command_json}")
        client.publish(MANAGER_TOPIC, command_json, qos=1)
    except Exception as e:
        print(f"发送模式切换指令失败: {e}")

def main():
    # 创建MQTT客户端
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
        client.loop_start()
        
        print("=== 云台控制测试开始 ===")
        time.sleep(2)  # 等待连接稳定
        
        # 测试1: 云台移动控制
        print("\n--- 测试1: 云台移动控制 ---")
        send_gimbal_control_command(client, {
            "command": "move",
            "pan": 45,
            "tilt": -30,
            "speed": 1.5
        })
        time.sleep(3)
        
        # 测试2: 缩放控制
        print("\n--- 测试2: 缩放控制 ---")
        send_gimbal_control_command(client, {
            "command": "zoom",
            "zoom": 2.0
        })
        time.sleep(3)
        
        # 测试3: 预设位置
        print("\n--- 测试3: 移动到预设位置 ---")
        send_gimbal_control_command(client, {
            "command": "preset",
            "preset_id": 2
        })
        time.sleep(3)
        
        # 测试4: 云台校准
        print("\n--- 测试4: 云台校准 ---")
        send_gimbal_control_command(client, {
            "command": "calibrate"
        })
        time.sleep(3)
        
        # 测试5: 重置云台
        print("\n--- 测试5: 重置云台 ---")
        send_gimbal_control_command(client, {
            "command": "reset"
        })
        time.sleep(3)
        
        # 测试6: 模式切换测试
        print("\n--- 测试6: 模式切换测试 ---")
        print("切换到手动模式...")
        send_mode_change_command(client, "manual")
        time.sleep(5)
        
        print("切换回自动模式...")
        send_mode_change_command(client, "auto")
        time.sleep(5)
        
        # 持续监控状态
        print("\n--- 持续监控云台状态 (按Ctrl+C退出) ---")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n测试结束")
            
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()