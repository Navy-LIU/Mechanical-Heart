#!/usr/bin/env python3
"""
云台设备模拟器
模拟Linux云台设备通过MQTT与聊天室服务器通信

功能:
1. 连接到MQTT服务器
2. 注册云台设备用户名"云台"
3. 订阅云台控制事件 (device/gimbal/control)
4. 接收并执行云台控制指令
5. 发送状态更新
"""
import json
import logging
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional
import paho.mqtt.client as mqtt
import argparse
import signal
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GimbalDevice")


class GimbalDeviceSimulator:
    """云台设备模拟器"""
    
    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883, 
                 device_id: str = None, username: str = None, password: str = None):
        """
        初始化云台设备模拟器
        
        Args:
            broker_host: MQTT代理服务器地址
            broker_port: MQTT代理服务器端口
            device_id: 设备唯一标识符
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        # 如果没有提供device_id，生成唯一ID避免客户端冲突
        self.device_id = device_id if device_id else f"gimbal_{int(time.time())}"
        self.username = "云台"  # 固定用户名
        
        # MQTT身份验证参数
        self.mqtt_username = username
        self.mqtt_password = password
        
        # MQTT客户端配置
        self.client = mqtt.Client(client_id=self.device_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # 设备状态
        self.is_connected = False
        self.is_running = False
        self.current_position = {"x": 2036, "y": 2125}  # 初始位置
        self.position_limits = {
            "x": {"min": 1024, "max": 3048},
            "y": {"min": 1850, "max": 2400}
        }
        
        # MQTT主题配置
        self.topics = {
            'control': 'device/gimbal/control',        # 接收控制指令
            'register': 'device/gimbal/register',      # 发送注册信息
            'status': 'device/gimbal/status',          # 发送状态更新
            'chat_in': 'chatroom/messages/in'          # 发送聊天消息（可选）
        }
        
        # 统计信息
        self.stats = {
            'connect_time': None,
            'commands_received': 0,
            'commands_executed': 0,
            'position_changes': 0,
            'last_command_time': None
        }
        
        # 状态发送定时器
        self.status_timer = None
        
        logger.info(f"云台设备模拟器初始化完成: {device_id} @ {broker_host}:{broker_port}")
    
    def start(self) -> bool:
        """
        启动云台设备模拟器
        
        Returns:
            启动是否成功
        """
        try:
            if self.is_running:
                logger.warning("云台设备已在运行")
                return True
            
            logger.info(f"连接到MQTT代理: {self.broker_host}:{self.broker_port}")
            
            # 设置MQTT身份验证
            if self.mqtt_username:
                logger.info(f"使用身份验证: {self.mqtt_username}")
                self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
            
            self.client.connect(self.broker_host, self.broker_port, 60)
            
            # 启动网络循环
            self.client.loop_start()
            self.is_running = True
            
            # 等待连接建立
            retry_count = 0
            while not self.is_connected and retry_count < 10:
                time.sleep(0.5)
                retry_count += 1
            
            if self.is_connected:
                logger.info("云台设备启动成功")
                
                # 注册设备
                self._register_device()
                
                # 启动状态发送定时器 (每30秒发送一次状态)
                self._start_status_timer()
                
                return True
            else:
                logger.error("MQTT连接超时")
                self.stop()
                return False
                
        except Exception as e:
            error_msg = str(e)
            if "No route to host" in error_msg or "10061" in error_msg:
                logger.error(f"云台设备启动失败: MQTT代理无法连接 ({self.broker_host}:{self.broker_port})")
                logger.error("请检查: 1) MQTT代理是否正在运行 2) 网络连接是否正常 3) IP地址和端口是否正确")
                if self.broker_host not in ["localhost", "127.0.0.1"]:
                    logger.info("建议: 在开发环境中使用 'localhost' 或 '127.0.0.1' 作为MQTT代理地址")
            elif "Connection refused" in error_msg:
                logger.error(f"云台设备启动失败: MQTT代理拒绝连接 ({self.broker_host}:{self.broker_port})")
                logger.error("请检查MQTT代理(Mosquitto)是否正在运行且监听此端口")
            else:
                logger.error(f"云台设备启动失败: {e}")
            return False
    
    def stop(self):
        """停止云台设备模拟器"""
        try:
            if not self.is_running:
                return
            
            logger.info("正在停止云台设备...")
            self.is_running = False
            
            # 停止状态定时器
            if self.status_timer:
                self.status_timer.cancel()
            
            # 发送离线状态
            self._send_offline_status()
            
            # 断开MQTT连接
            self.client.loop_stop()
            self.client.disconnect()
            
            logger.info("云台设备已停止")
            
        except Exception as e:
            logger.error(f"停止云台设备异常: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT连接成功回调"""
        if rc == 0:
            logger.info("云台设备MQTT连接成功")
            self.is_connected = True
            self.stats['connect_time'] = datetime.now()
            
            # 订阅云台控制主题
            client.subscribe(self.topics['control'])
            logger.info(f"订阅云台控制主题: {self.topics['control']}")
        else:
            logger.error(f"MQTT连接失败，返回码: {rc}")
            self.is_connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT断开连接回调"""
        self.is_connected = False
        if rc != 0:
            logger.warning(f"云台设备MQTT意外断开连接，返回码: {rc}")
        else:
            logger.info("云台设备MQTT正常断开连接")
    
    def _on_message(self, client, userdata, msg):
        """MQTT消息接收回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logger.info(f"收到MQTT消息: {topic} -> {payload}")
            
            if topic == self.topics['control']:
                self._handle_control_message(payload)
            
        except Exception as e:
            logger.error(f"处理MQTT消息异常: {e}")
    
    def _handle_control_message(self, payload: str):
        """
        处理云台控制消息
        消息格式: "Ang_X=2036,Ang_Y=2125"
        
        Args:
            payload: 控制消息内容
        """
        try:
            logger.info(f"收到云台控制指令: {payload}")
            self.stats['commands_received'] += 1
            
            # 解析控制参数
            control_params = self._parse_control_command(payload)
            if control_params:
                # 执行云台控制
                success = self._execute_gimbal_control(
                    control_params['ang_x'], 
                    control_params['ang_y']
                )
                
                if success:
                    self.stats['commands_executed'] += 1
                    self.stats['last_command_time'] = datetime.now()
                    
                    # 发送执行成功的反馈消息到聊天室
                    self._send_chat_feedback(
                        f"✅ 云台已移动到位置: X={control_params['ang_x']}, Y={control_params['ang_y']}"
                    )
            
        except Exception as e:
            logger.error(f"处理控制消息异常: {e}")
            
            # 发送错误反馈到聊天室
            self._send_chat_feedback(f"❌ 云台控制失败: {str(e)}")
    
    def _parse_control_command(self, payload: str) -> Optional[Dict[str, int]]:
        """
        解析云台控制命令
        支持格式: "Ang_X=2036,Ang_Y=2125"
        
        Args:
            payload: 控制命令字符串
            
        Returns:
            解析后的控制参数，如果解析失败返回None
        """
        try:
            import re
            
            # 使用正则表达式解析
            x_match = re.search(r'Ang_X=(\d+)', payload)
            y_match = re.search(r'Ang_Y=(\d+)', payload)
            
            if x_match and y_match:
                ang_x = int(x_match.group(1))
                ang_y = int(y_match.group(1))
                
                # 验证参数范围
                if (self.position_limits['x']['min'] <= ang_x <= self.position_limits['x']['max'] and
                    self.position_limits['y']['min'] <= ang_y <= self.position_limits['y']['max']):
                    
                    return {
                        'ang_x': ang_x,
                        'ang_y': ang_y
                    }
                else:
                    logger.error(f"云台控制参数超出范围: X={ang_x}, Y={ang_y}")
                    return None
            else:
                logger.error(f"云台控制命令格式错误: {payload}")
                return None
                
        except Exception as e:
            logger.error(f"解析云台控制命令异常: {e}")
            return None
    
    def _execute_gimbal_control(self, target_x: int, target_y: int) -> bool:
        """
        执行云台控制，模拟云台移动
        
        Args:
            target_x: 目标X位置
            target_y: 目标Y位置
            
        Returns:
            执行是否成功
        """
        try:
            current_x = self.current_position['x']
            current_y = self.current_position['y']
            
            logger.info(f"云台开始移动: ({current_x}, {current_y}) -> ({target_x}, {target_y})")
            
            # 计算移动距离和时间
            distance_x = abs(target_x - current_x)
            distance_y = abs(target_y - current_y)
            total_distance = (distance_x**2 + distance_y**2)**0.5
            
            # 模拟移动时间（基于距离，每1000单位约需要1秒）
            move_time = max(0.1, total_distance / 1000)
            logger.info(f"预计移动时间: {move_time:.2f}秒")
            
            # 模拟移动过程（在后台线程中）
            def move_gimbal():
                try:
                    time.sleep(move_time)
                    
                    # 更新位置
                    self.current_position['x'] = target_x
                    self.current_position['y'] = target_y
                    self.stats['position_changes'] += 1
                    
                    logger.info(f"云台移动完成: 当前位置 ({target_x}, {target_y})")
                    logger.info(f"云台控制执行成功: X={target_x}, Y={target_y}")
                    
                    # 立即发送状态更新
                    self._send_status_update()
                    
                except Exception as e:
                    logger.error(f"云台移动异常: {e}")
            
            # 在新线程中执行移动
            move_thread = threading.Thread(target=move_gimbal)
            move_thread.daemon = True
            move_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"执行云台控制异常: {e}")
            return False
    
    def _register_device(self):
        """向服务器注册云台设备"""
        try:
            register_data = {
                'client_id': self.device_id,
                'username': self.username,
                'device_type': 'gimbal',
                'device_info': {
                    'model': 'Simulated Gimbal v1.0',
                    'position_limits': self.position_limits,
                    'current_position': self.current_position,
                    'capabilities': ['angle_control', 'position_feedback']
                }
            }
            
            message = json.dumps(register_data)
            self.client.publish(self.topics['register'], message)
            
            logger.info(f"云台设备注册信息已发送: {self.username} ({self.device_id})")
            
        except Exception as e:
            logger.error(f"注册云台设备异常: {e}")
    
    def _send_status_update(self):
        """发送云台状态更新"""
        try:
            status_data = {
                'client_id': self.device_id,
                'status': 'online',
                'current_position': self.current_position,
                'timestamp': datetime.now().isoformat(),
                'stats': {
                    'connect_time': self.stats['connect_time'].isoformat() if self.stats['connect_time'] else None,
                    'commands_received': self.stats['commands_received'],
                    'commands_executed': self.stats['commands_executed'],
                    'position_changes': self.stats['position_changes'],
                    'last_command_time': self.stats['last_command_time'].isoformat() if self.stats['last_command_time'] else None
                }
            }
            
            message = json.dumps(status_data)
            self.client.publish(self.topics['status'], message)
            
        except Exception as e:
            logger.error(f"发送状态更新异常: {e}")
    
    def _send_offline_status(self):
        """发送离线状态"""
        try:
            status_data = {
                'client_id': self.device_id,
                'status': 'offline',
                'current_position': self.current_position,
                'timestamp': datetime.now().isoformat()
            }
            
            message = json.dumps(status_data)
            self.client.publish(self.topics['status'], message)
            
            logger.info("云台离线状态已发送")
            
            # 等待消息发送完成
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"发送离线状态异常: {e}")
    
    def _send_chat_feedback(self, message: str):
        """
        向聊天室发送反馈消息
        
        Args:
            message: 要发送的消息内容
        """
        try:
            chat_data = {
                'client_id': self.device_id,
                'username': f'{self.username} (设备)',
                'message': message
            }
            
            chat_message = json.dumps(chat_data)
            self.client.publish(self.topics['chat_in'], chat_message)
            
        except Exception as e:
            logger.error(f"发送聊天反馈异常: {e}")
    
    def _start_status_timer(self):
        """启动状态发送定时器"""
        try:
            # 发送一次初始状态
            self._send_status_update()
            
            # 启动定时器，每30秒发送一次状态
            def send_periodic_status():
                if self.is_running and self.is_connected:
                    self._send_status_update()
                    # 设置下一次定时器
                    if self.is_running:
                        self.status_timer = threading.Timer(30.0, send_periodic_status)
                        self.status_timer.daemon = True
                        self.status_timer.start()
            
            self.status_timer = threading.Timer(30.0, send_periodic_status)
            self.status_timer.daemon = True
            self.status_timer.start()
            
            logger.info("状态发送定时器已启动 (30秒间隔)")
            
        except Exception as e:
            logger.error(f"启动状态定时器异常: {e}")


def signal_handler(sig, frame):
    """信号处理器，用于优雅关闭"""
    global gimbal_device
    print(f"\n收到信号 {sig}，正在关闭云台设备...")
    if gimbal_device:
        gimbal_device.stop()
    sys.exit(0)


def main():
    """主函数"""
    global gimbal_device
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='云台设备模拟器')
    parser.add_argument('--host', default='localhost', help='MQTT代理服务器地址 (默认: localhost)')
    parser.add_argument('--port', type=int, default=1883, help='MQTT代理服务器端口 (默认: 1883)')
    parser.add_argument('--device-id', help='设备唯一标识符 (默认: 自动生成)')
    parser.add_argument('--username', help='MQTT认证用户名 (可选)')
    parser.add_argument('--password', help='MQTT认证密码 (可选)')
    parser.add_argument('--log-level', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO',
                       help='日志级别 (默认: INFO)')
    
    args = parser.parse_args()
    
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建并启动云台设备模拟器
    gimbal_device = GimbalDeviceSimulator(
        broker_host=args.host,
        broker_port=args.port,
        device_id=args.device_id,
        username=args.username,
        password=args.password
    )
    
    print("云台设备模拟器 v1.0")
    print(f"设备ID: {args.device_id}")
    print(f"MQTT代理: {args.host}:{args.port}")
    print("按 Ctrl+C 退出")
    print("-" * 50)
    
    # 启动设备
    if gimbal_device.start():
        try:
            # 保持程序运行
            while gimbal_device.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n收到键盘中断，正在关闭...")
        finally:
            gimbal_device.stop()
    else:
        print("云台设备启动失败")
        return 1
    
    return 0


# 全局变量
gimbal_device = None

if __name__ == "__main__":
    sys.exit(main())