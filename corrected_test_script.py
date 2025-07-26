#!/usr/bin/env python3
"""
修正版测试脚本：演示如何使用正确的MQTT主题进行云台控制和状态监控
"""

import paho.mqtt.client as mqtt
import json
import time

# MQTT配置
MQTT_BROKER_HOST = "192.168.137.1"
MQTT_BROKER_PORT = 1883

# 正确的MQTT主题
MANAGER_TOPIC = "camera/manager/set_mode"      # 服务器调整云台运行模式 (服务器 -> 云台)
TRACKING_STATUS_TOPIC = "camera/tracking/set_mode"  # 云台发布自身运行模式 (云台 -> 服务器)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("测试客户端已连接到MQTT服务器")
        # 订阅云台状态主题以监控状态变化
        client.subscribe(TRACKING_STATUS_TOPIC)
        print(f"已订阅云台状态主题: {TRACKING_STATUS_TOPIC}")
    else:
        print(f"连接失败，返回码: {rc}")

def on_message(client, userdata, msg):
    """处理收到的云台状态消息"""
    if msg.topic == TRACKING_STATUS_TOPIC:
        try:
            status = json.loads(msg.payload.decode('utf-8'))
            print(f"\n[云台状态更新]: {json.dumps(status, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"解析状态消息失败: {e}")

def send_command(client, command):
    """发送指令到管理主题"""
    try:
        command_json = json.dumps(command, ensure_ascii=False)
        print(f"\n发送指令: {command_json}")
        client.publish(MANAGER_TOPIC, command_json, qos=1)
    except Exception as e:
        print(f"发送指令失败: {e}")

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
        
        # 测试1: 模式切换
        print("\n--- 测试1: 模式切换 ---")
        print("切换到手动模式...")
        send_command(client, {"mode": "manual"})
        time.sleep(5)
        
        print("切换回自动模式...")
        send_command(client, {"mode": "auto"})
        time.sleep(5)
        
        # 测试2: 云台移动控制
        print("\n--- 测试2: 云台移动控制 ---")
        send_command(client, {
            "command": "move",
            "pan": 45,
            "tilt": -30,
            "speed": 1.5
        })
        time.sleep(3)
        
        # 测试3: 缩放控制
        print("\n--- 测试3: 缩放控制 ---")
        send_command(client, {
            "command": "zoom",
            "zoom": 2.0
        })
        time.sleep(3)
        
        # 测试4: 预设位置
        print("\n--- 测试4: 移动到预设位置 ---")
        send_command(client, {
            "command": "preset",
            "preset_id": 2
        })
        time.sleep(3)
        
        # 测试5: 云台校准
        print("\n--- 测试5: 云台校准 ---")
        send_command(client, {
            "command": "calibrate"
        })
        time.sleep(3)
        
        # 测试6: 重置云台
        print("\n--- 测试6: 重置云台 ---")
        send_command(client, {
            "command": "reset"
        })
        time.sleep(3)
        
        # 测试7: 组合测试（先切换模式，再控制云台）
        print("\n--- 测试7: 组合测试 ---")
        print("切换到手动模式...")
        send_command(client, {"mode": "manual"})
        time.sleep(2)
        
        print("在手动模式下移动云台...")
        send_command(client, {
            "command": "move",
            "pan": -45,
            "tilt": 15
        })
        time.sleep(3)
        
        print("切换回自动模式...")
        send_command(client, {"mode": "auto"})
        time.sleep(3)
        
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