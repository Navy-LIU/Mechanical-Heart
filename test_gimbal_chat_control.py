#!/usr/bin/env python3
"""
云台聊天室控制测试脚本
测试通过聊天室@云台指令控制云台设备的完整流程
"""
import requests
import json
import time
import logging
import argparse
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GimbalChatTest")


class GimbalChatControlTest:
    """云台聊天控制测试类"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """
        初始化测试类
        
        Args:
            base_url: 聊天室服务器地址
        """
        self.base_url = base_url.rstrip('/')
        self.test_username = f"测试用户_{int(time.time())}"
        self.session = requests.Session()
    
    def test_health_check(self) -> bool:
        """测试服务器健康状态"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                logger.info("✅ 服务器健康检查通过")
                return True
            else:
                logger.error(f"❌ 服务器健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ 无法连接到服务器: {e}")
            return False
    
    def get_mqtt_status(self) -> dict:
        """获取MQTT服务状态"""
        try:
            response = self.session.get(f"{self.base_url}/mqtt/status")
            if response.status_code == 200:
                status = response.json()
                logger.info("📊 MQTT状态:")
                logger.info(f"  - 连接状态: {status.get('is_connected')}")
                logger.info(f"  - 云台设备数量: {status.get('gimbal_devices_count', 0)}")
                logger.info(f"  - 云台在线状态: {status.get('is_gimbal_online', False)}")
                logger.info(f"  - 已发送指令数: {status.get('gimbal_commands_sent', 0)}")
                return status
            else:
                logger.error(f"❌ 获取MQTT状态失败: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"❌ 获取MQTT状态异常: {e}")
            return {}
    
    def send_gimbal_command(self, ang_x: int, ang_y: int) -> bool:
        """
        发送云台控制指令
        
        Args:
            ang_x: X轴角度
            ang_y: Y轴角度
            
        Returns:
            是否发送成功
        """
        try:
            # 构建@云台控制消息
            message = f"@云台 云台控制 Ang_x={ang_x} Ang_Y={ang_y}"
            
            # 使用URL快速发送接口
            payload = {
                "username": self.test_username,
                "message": message,
                "display_name": "云台测试用户"
            }
            
            logger.info(f"🎯 发送云台控制指令: X={ang_x}, Y={ang_y}")
            logger.info(f"📝 消息内容: {message}")
            
            response = self.session.post(
                f"{self.base_url}/quick-send",
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ 消息发送成功")
                logger.info(f"📤 发送结果: {result.get('message', 'OK')}")
                return True
            else:
                logger.error(f"❌ 消息发送失败: {response.status_code}")
                logger.error(f"📤 错误信息: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 发送云台控制指令异常: {e}")
            return False
    
    def test_gimbal_command_formats(self):
        """测试不同的云台指令格式"""
        test_cases = [
            {"ang_x": 2036, "ang_y": 2125, "desc": "中心位置"},
            {"ang_x": 1500, "ang_y": 2000, "desc": "左侧位置"},
            {"ang_x": 2800, "ang_y": 2200, "desc": "右侧位置"},
            {"ang_x": 2036, "ang_y": 1900, "desc": "下方位置"},
            {"ang_x": 2036, "ang_y": 2300, "desc": "上方位置"}
        ]
        
        logger.info("🧪 开始测试不同云台控制指令格式")
        logger.info("=" * 50)
        
        for i, case in enumerate(test_cases, 1):
            logger.info(f"📋 测试案例 {i}: {case['desc']}")
            
            # 发送指令
            success = self.send_gimbal_command(case['ang_x'], case['ang_y'])
            
            if success:
                logger.info(f"✅ 测试案例 {i} 成功")
            else:
                logger.error(f"❌ 测试案例 {i} 失败")
            
            # 等待指令处理
            logger.info("⏳ 等待3秒...")
            time.sleep(3)
            
            logger.info("-" * 30)
    
    def test_invalid_commands(self):
        """测试无效的云台指令"""
        invalid_cases = [
            "@云台 Ang_x=999 Ang_Y=2000",      # X轴超出下限
            "@云台 Ang_x=4000 Ang_Y=2000",     # X轴超出上限  
            "@云台 Ang_x=2000 Ang_Y=1000",     # Y轴超出下限
            "@云台 Ang_x=2000 Ang_Y=3000",     # Y轴超出上限
            "@云台 Ang_x=abc Ang_Y=2000",      # 非数字参数
            "@云台 错误的指令格式",              # 格式错误
        ]
        
        logger.info("🧪 开始测试无效云台控制指令")
        logger.info("=" * 50)
        
        for i, message in enumerate(invalid_cases, 1):
            logger.info(f"📋 无效测试案例 {i}: {message}")
            
            payload = {
                "username": self.test_username,
                "message": message
            }
            
            try:
                response = self.session.post(
                    f"{self.base_url}/quick-send",
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    logger.info("✅ 消息发送成功（应该被系统拒绝）")
                else:
                    logger.warning(f"⚠️ 消息发送失败: {response.status_code}")
                
            except Exception as e:
                logger.error(f"❌ 发送异常: {e}")
            
            time.sleep(2)
            logger.info("-" * 30)
    
    def run_full_test(self):
        """运行完整测试"""
        logger.info("🚀 开始云台聊天控制完整测试")
        logger.info("=" * 60)
        
        # 1. 健康检查
        if not self.test_health_check():
            logger.error("❌ 服务器健康检查失败，终止测试")
            return
        
        # 2. 获取MQTT状态
        mqtt_status = self.get_mqtt_status()
        if not mqtt_status.get('is_connected'):
            logger.warning("⚠️ MQTT服务未连接，但继续测试")
        
        logger.info("=" * 60)
        
        # 3. 测试有效指令
        self.test_gimbal_command_formats()
        
        logger.info("=" * 60)
        
        # 4. 测试无效指令
        self.test_invalid_commands()
        
        logger.info("=" * 60)
        
        # 5. 最终状态检查
        logger.info("📊 最终MQTT状态:")
        final_status = self.get_mqtt_status()
        
        logger.info("=" * 60)
        logger.info("🎉 云台聊天控制测试完成!")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='云台聊天控制测试脚本')
    parser.add_argument('--url', default='http://localhost:5000', 
                       help='聊天室服务器URL')
    parser.add_argument('--test-type', choices=['full', 'valid', 'invalid'], 
                       default='full', help='测试类型')
    parser.add_argument('--x', type=int, help='单独测试X轴角度')
    parser.add_argument('--y', type=int, help='单独测试Y轴角度')
    
    args = parser.parse_args()
    
    print("🎥 云台聊天控制测试脚本 v1.0")
    print(f"🌐 服务器: {args.url}")
    print("=" * 50)
    
    # 创建测试实例
    tester = GimbalChatControlTest(args.url)
    
    if args.x is not None and args.y is not None:
        # 单独指令测试
        logger.info(f"🎯 单独测试指令: X={args.x}, Y={args.y}")
        tester.test_health_check()
        tester.get_mqtt_status()
        tester.send_gimbal_command(args.x, args.y)
    elif args.test_type == 'full':
        # 完整测试
        tester.run_full_test()
    elif args.test_type == 'valid':
        # 仅测试有效指令
        tester.test_health_check()
        tester.get_mqtt_status()
        tester.test_gimbal_command_formats()
    elif args.test_type == 'invalid':
        # 仅测试无效指令
        tester.test_health_check()
        tester.test_invalid_commands()


if __name__ == "__main__":
    main()