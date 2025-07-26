#!/usr/bin/env python3
"""
云台控制MQTT测试脚本
用于测试通过MQTT发送云台控制命令
"""
import json
import time
import logging
import paho.mqtt.client as mqtt

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GimbalControlTester:
    """云台控制测试器"""
    
    def __init__(self, broker_host="localhost", broker_port=1883):
        """
        初始化测试器
        
        Args:
            broker_host: MQTT代理服务器地址
            broker_port: MQTT代理服务器端口
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        
        # MQTT客户端
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # 主题配置
        self.gimbal_topic = "device/gimbal/control"
        self.system_topic = "chatroom/system"
        
        # 状态
        self.is_connected = False
        
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self.is_connected = True
            logger.info("MQTT连接成功")
            
            # 订阅系统消息主题以接收反馈
            client.subscribe(self.system_topic)
            logger.info(f"订阅系统消息主题: {self.system_topic}")
            
        else:
            logger.error(f"MQTT连接失败，错误代码: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        self.is_connected = False
        logger.info(f"MQTT连接断开，代码: {rc}")
    
    def _on_message(self, client, userdata, message):
        """消息回调"""
        try:
            topic = message.topic
            payload = message.payload.decode('utf-8')
            
            logger.info(f"收到消息: {topic} -> {payload}")
            
        except Exception as e:
            logger.error(f"处理消息异常: {e}")
    
    def connect(self):
        """连接到MQTT代理"""
        try:
            logger.info(f"连接到MQTT代理: {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # 等待连接
            retry_count = 0
            while not self.is_connected and retry_count < 10:
                time.sleep(0.5)
                retry_count += 1
            
            return self.is_connected
            
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.is_connected:
            self.client.loop_stop()
            self.client.disconnect()
    
    def send_gimbal_command(self, ang_x, ang_y):
        """
        发送云台控制命令
        
        Args:
            ang_x: X轴角度
            ang_y: Y轴角度
        """
        if not self.is_connected:
            logger.error("MQTT未连接")
            return False
        
        try:
            # 构造命令
            command = f"Ang_X={ang_x},Ang_Y={ang_y}"
            
            # 发送命令
            self.client.publish(self.gimbal_topic, command)
            logger.info(f"发送云台控制命令: {command}")
            
            return True
            
        except Exception as e:
            logger.error(f"发送命令失败: {e}")
            return False
    
    def run_test_suite(self):
        """运行测试套件"""
        logger.info("开始云台控制测试")
        
        # 连接到MQTT
        if not self.connect():
            logger.error("无法连接到MQTT代理")
            return
        
        try:
            # 等待一秒以确保连接稳定
            time.sleep(1)
            
            # 测试用例
            test_cases = [
                # 正常情况
                {"name": "正常情况1", "x": 2036, "y": 2125},
                {"name": "正常情况2", "x": 1024, "y": 1850},  # 最小值
                {"name": "正常情况3", "x": 3048, "y": 2400},  # 最大值
                {"name": "正常情况4", "x": 2000, "y": 2000},  # 中间值
                
                # 边界情况
                {"name": "X边界测试", "x": 1023, "y": 2000},  # X超出下限
                {"name": "X边界测试", "x": 3049, "y": 2000},  # X超出上限
                {"name": "Y边界测试", "x": 2000, "y": 1849},  # Y超出下限
                {"name": "Y边界测试", "x": 2000, "y": 2401},  # Y超出上限
            ]
            
            for i, case in enumerate(test_cases):
                logger.info(f"\n=== 测试用例 {i+1}: {case['name']} ===")
                self.send_gimbal_command(case['x'], case['y'])
                
                # 等待处理
                time.sleep(2)
            
            # 发送格式错误的命令测试
            logger.info("\n=== 格式错误测试 ===")
            
            error_commands = [
                "X=2036,Y=2125",  # 缺少Ang_前缀
                "Ang_X=2036,Ang_Z=2125",  # 错误的轴名
                "Ang_X=abc,Ang_Y=2125",  # 非数字
                "Ang_X=2036",  # 缺少Y参数
                "Ang_X=2036,Ang_Y=2125,Extra=123"  # 多余参数
            ]
            
            for cmd in error_commands:
                logger.info(f"发送错误格式命令: {cmd}")
                self.client.publish(self.gimbal_topic, cmd)
                time.sleep(1.5)
            
            logger.info("\n测试完成，等待5秒接收反馈...")
            time.sleep(5)
            
        finally:
            self.disconnect()
            logger.info("测试结束")


def main():
    """主函数"""
    print("云台控制MQTT测试脚本")
    print("=" * 50)
    
    # 创建测试器
    tester = GimbalControlTester()
    
    try:
        # 运行测试
        tester.run_test_suite()
        
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试异常: {e}")
    finally:
        tester.disconnect()


if __name__ == "__main__":
    main()