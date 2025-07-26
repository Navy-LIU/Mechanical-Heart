import subprocess
import paho.mqtt.client as mqtt
import json
import time
import os
import signal
import threading

# ======================= 1. 配置信息 =======================

# 请将这里的IP地址修改为你MQTT服务器的实际IP地址
MQTT_BROKER_HOST = "192.168.137.1" 
MQTT_BROKER_PORT = 1883

# --- 路径配置 (!! 非常重要，请根据你的实际路径修改 !!) ---
# C++ "自动进程" 可执行文件的绝对路径
PATH_TO_AUTO_PROCESS_EXECUTABLE = "/root/insta360_link_uvc_ctrl/build/V4L2Capture"

# Python "手动进程" 脚本的绝对路径
PATH_TO_MANUAL_PROCESS_SCRIPT = "/root/hand/gimbal_device_simulator.py --host 192.168.137.1 --port 1883"

# --- MQTT 主题配置 ---
# 总指挥用来接收模式切换指令的主题
MANAGER_TOPIC = "camera/manager/set_mode"

# 用于控制C++自动进程"暂停/恢复"的主题
AUTO_PROCESS_CONTROL_TOPIC = "camera/tracking/set_mode"

# ===== 新增的MQTT主题 =====
# 服务器控制云台的主题 (服务器 -> 云台)
GIMBAL_CONTROL_TOPIC = "camera/gimbal/control"

# 云台状态发布主题 (云台 -> 服务器)
GIMBAL_STATUS_TOPIC = "camera/gimbal/status"

# ==========================================================

# --- 全局状态变量 ---
current_mode = "idle"  # 当前模式: idle, auto, manual
auto_process = None    # 存放自动进程的Popen对象
manual_process = None  # 存放手动进程的Popen对象

# ===== 新增的云台状态变量 =====
gimbal_status = {
    "pan": 0.0,      # 云台水平角度 (-180 到 180)
    "tilt": 0.0,     # 云台俯仰角度 (-90 到 90)
    "roll": 0.0,     # 云台翻滚角度 (-180 到 180)
    "zoom": 1.0,     # 缩放倍数
    "mode": "idle",  # 云台模式: idle, tracking, manual_control
    "online": True,  # 云台是否在线
    "battery": 100   # 电池电量百分比 (如果适用)
}

# 全局MQTT客户端
mqtt_client = mqtt.Client()

# 状态发布线程控制
status_publish_thread = None
stop_status_publish = False

def start_auto_process():
    """启动C++自动进程，并告诉它进入'auto'模式"""
    global auto_process, current_mode
    if auto_process is None or auto_process.poll() is not None:
        print("[管理器]: 正在启动'自动进程'...")
        # 获取可执行文件所在的目录
        cwd = os.path.dirname(PATH_TO_AUTO_PROCESS_EXECUTABLE)
        auto_process = subprocess.Popen([PATH_TO_AUTO_PROCESS_EXECUTABLE], cwd=cwd)
        print(f"[管理器]: '自动进程'已启动 (PID: {auto_process.pid})。")
        # 等待一下，确保它有足够时间订阅MQTT
        time.sleep(2)
    
    # 发送指令让它开始追踪
    mqtt_client.publish(AUTO_PROCESS_CONTROL_TOPIC, '{"mode":"auto"}', qos=1)
    print(f"[管理器]: 已向'自动进程'发送'auto'指令。")
    current_mode = "auto"
    
    # 更新云台状态
    update_gimbal_status(mode="tracking")

def stop_auto_process():
    """暂停C++自动进程（不杀死它，而是让它待机）"""
    global current_mode
    # 发送指令让它停止追踪
    mqtt_client.publish(AUTO_PROCESS_CONTROL_TOPIC, '{"mode":"pause"}', qos=1)
    print(f"[管理器]: 已向'自动进程'发送'pause'指令。")
    if current_mode == "auto":
        current_mode = "idle"
    
    # 更新云台状态
    update_gimbal_status(mode="idle")

def start_manual_process():
    """启动Python手动进程"""
    global manual_process, current_mode
    if manual_process is None or manual_process.poll() is not None:
        print("[管理器]: 正在启动'手动进程'...")
        manual_process = subprocess.Popen(["python3", PATH_TO_MANUAL_PROCESS_SCRIPT])
        print(f"[管理器]: '手动进程'已启动 (PID: {manual_process.pid})。")
    current_mode = "manual"
    
    # 更新云台状态
    update_gimbal_status(mode="manual_control")

def stop_manual_process():
    """终止Python手动进程"""
    global manual_process, current_mode
    if manual_process and manual_process.poll() is None:
        print(f"[管理器]: 正在终止'手动进程' (PID: {manual_process.pid})...")
        manual_process.terminate() # 发送终止信号
        manual_process.wait() # 等待进程结束
        print("[管理器]: '手动进程'已终止。")
    if current_mode == "manual":
        current_mode = "idle"
    
    # 更新云台状态
    update_gimbal_status(mode="idle")

# ===== 新增的云台控制和状态功能 =====

def update_gimbal_status(**kwargs):
    """更新云台状态"""
    global gimbal_status
    for key, value in kwargs.items():
        if key in gimbal_status:
            gimbal_status[key] = value
            print(f"[云台状态]: {key} 更新为 {value}")

def handle_gimbal_control(command_data):
    """处理服务器发送的云台控制指令"""
    try:
        print(f"[云台控制]: 收到控制指令 -> {command_data}")
        
        command_type = command_data.get("command")
        
        if command_type == "move":
            # 云台移动指令
            pan = command_data.get("pan", gimbal_status["pan"])
            tilt = command_data.get("tilt", gimbal_status["tilt"])
            speed = command_data.get("speed", 1.0)  # 移动速度
            
            print(f"[云台控制]: 移动云台到位置 Pan: {pan}°, Tilt: {tilt}°, 速度: {speed}")
            
            # 这里应该调用实际的云台控制代码
            # 例如通过串口或其他方式控制云台硬件
            # gimbal_hardware.move_to(pan, tilt, speed)
            
            # 模拟云台移动（实际应用中应该从硬件获取真实位置）
            update_gimbal_status(pan=pan, tilt=tilt)
            
        elif command_type == "zoom":
            # 缩放控制
            zoom_level = command_data.get("zoom", gimbal_status["zoom"])
            print(f"[云台控制]: 设置缩放级别为 {zoom_level}x")
            
            # 这里应该调用实际的缩放控制代码
            # camera_control.set_zoom(zoom_level)
            
            update_gimbal_status(zoom=zoom_level)
            
        elif command_type == "preset":
            # 预设位置
            preset_id = command_data.get("preset_id")
            print(f"[云台控制]: 移动到预设位置 {preset_id}")
            
            # 预定义一些预设位置
            presets = {
                1: {"pan": 0, "tilt": 0},      # 正前方
                2: {"pan": 90, "tilt": -30},   # 右前方俯视
                3: {"pan": -90, "tilt": -30},  # 左前方俯视
                4: {"pan": 180, "tilt": 0},    # 正后方
            }
            
            if preset_id in presets:
                preset_pos = presets[preset_id]
                update_gimbal_status(**preset_pos)
                print(f"[云台控制]: 已移动到预设位置 {preset_id}: {preset_pos}")
            else:
                print(f"[云台控制]: 未知的预设位置 {preset_id}")
                
        elif command_type == "calibrate":
            # 云台校准
            print("[云台控制]: 开始云台校准...")
            # 这里应该调用云台校准程序
            # gimbal_hardware.calibrate()
            update_gimbal_status(pan=0, tilt=0, roll=0)
            print("[云台控制]: 云台校准完成")
            
        elif command_type == "reset":
            # 重置云台位置
            print("[云台控制]: 重置云台到初始位置...")
            update_gimbal_status(pan=0, tilt=0, roll=0, zoom=1.0)
            print("[云台控制]: 云台已重置")
            
        else:
            print(f"[云台控制]: 未知的控制指令: {command_type}")
            
    except Exception as e:
        print(f"[云台控制]: 处理控制指令时出错: {e}")

def publish_gimbal_status():
    """定期发布云台状态"""
    global stop_status_publish
    while not stop_status_publish:
        try:
            # 添加时间戳
            status_with_timestamp = gimbal_status.copy()
            status_with_timestamp["timestamp"] = int(time.time() * 1000)  # 毫秒时间戳
            
            # 发布状态
            status_json = json.dumps(status_with_timestamp)
            mqtt_client.publish(GIMBAL_STATUS_TOPIC, status_json, qos=1)
            
            # 每秒发布一次状态
            time.sleep(1)
            
        except Exception as e:
            print(f"[状态发布]: 发布云台状态时出错: {e}")
            time.sleep(1)

def start_status_publishing():
    """启动状态发布线程"""
    global status_publish_thread, stop_status_publish
    if status_publish_thread is None or not status_publish_thread.is_alive():
        stop_status_publish = False
        status_publish_thread = threading.Thread(target=publish_gimbal_status, daemon=True)
        status_publish_thread.start()
        print("[状态发布]: 云台状态发布线程已启动")

def stop_status_publishing():
    """停止状态发布线程"""
    global stop_status_publish
    stop_status_publish = True
    print("[状态发布]: 云台状态发布线程已停止")

# MQTT回调函数
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[管理器]: 成功连接到MQTT服务器。")
        
        # 订阅原有主题
        client.subscribe(MANAGER_TOPIC)
        print(f"[管理器]: 已订阅管理主题: {MANAGER_TOPIC}")
        
        # 订阅新增的云台控制主题
        client.subscribe(GIMBAL_CONTROL_TOPIC)
        print(f"[管理器]: 已订阅云台控制主题: {GIMBAL_CONTROL_TOPIC}")
        
        # 启动状态发布
        start_status_publishing()
        
    else:
        print(f"[管理器]: 连接失败，返回码: {rc}")

def on_message(client, userdata, msg):
    """处理MQTT消息"""
    global current_mode
    
    topic = msg.topic
    payload_str = msg.payload.decode('utf-8')
    print(f"\n[MQTT消息]: 主题: {topic}, 内容: {payload_str}")
    
    try:
        data = json.loads(payload_str)
        
        if topic == MANAGER_TOPIC:
            # 原有的模式切换逻辑
            target_mode = data.get("mode")
            if target_mode == "manual":
                if current_mode != "manual":
                    print("[管理器]: 正在切换到手动模式...")
                    stop_auto_process()  # 先暂停自动进程
                    start_manual_process() # 再启动手动进程
                    print("[管理器]: 已切换到手动模式。")
                else:
                    print("[管理器]: 已处于手动模式，无需切换。")
            elif target_mode == "auto":
                if current_mode != "auto":
                    print("[管理器]: 正在切换到自动模式...")
                    stop_manual_process() # 先停止手动进程
                    start_auto_process()  # 再恢复自动进程
                    print("[管理器]: 已切换到自动模式。")
                else:
                    print("[管理器]: 已处于自动模式，无需切换。")
            else:
                print(f"[管理器]: 未知的模式指令: {target_mode}")
                
        elif topic == GIMBAL_CONTROL_TOPIC:
            # 新增的云台控制逻辑
            handle_gimbal_control(data)
            
    except Exception as e:
        print(f"[MQTT消息]: 处理消息时出错: {e}")

# --- 主程序 ---
def main():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    try:
        mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
    except Exception as e:
        print(f"[管理器]: 无法连接到MQTT服务器: {e}")
        return

    # 默认启动时，先启动自动进程
    start_auto_process()

    try:
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        print("\n[管理器]: 程序被用户中断。")
    finally:
        print("[管理器]: 正在清理所有子进程...")
        
        # 停止状态发布
        stop_status_publishing()
        
        # 确保所有子进程都被关闭
        if auto_process and auto_process.poll() is None:
            auto_process.terminate()
            auto_process.wait()
        if manual_process and manual_process.poll() is None:
            manual_process.terminate()
            manual_process.wait()

if __name__ == "__main__":
    main()