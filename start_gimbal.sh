#!/bin/bash
"""
云台设备模拟器启动脚本
"""

# 默认配置
DEFAULT_HOST="localhost"
DEFAULT_PORT="1883"
DEFAULT_DEVICE_ID="gimbal_001"
DEFAULT_LOG_LEVEL="INFO"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🎥 云台设备模拟器启动脚本${NC}"
echo "=================================="

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 python3${NC}"
    exit 1
fi

# 检查paho-mqtt是否安装
if ! python3 -c "import paho.mqtt.client" &> /dev/null; then
    echo -e "${YELLOW}警告: paho-mqtt 未安装，正在安装...${NC}"
    pip3 install paho-mqtt
    if [ $? -ne 0 ]; then
        echo -e "${RED}错误: 无法安装 paho-mqtt${NC}"
        exit 1
    fi
fi

# 解析命令行参数
HOST=${1:-$DEFAULT_HOST}
PORT=${2:-$DEFAULT_PORT}
DEVICE_ID=${3:-$DEFAULT_DEVICE_ID}
LOG_LEVEL=${4:-$DEFAULT_LOG_LEVEL}

echo "配置信息:"
echo "  MQTT代理: $HOST:$PORT"
echo "  设备ID: $DEVICE_ID"
echo "  日志级别: $LOG_LEVEL"
echo ""

# 检查云台模拟器文件是否存在
if [ ! -f "gimbal_device_simulator.py" ]; then
    echo -e "${RED}错误: 未找到 gimbal_device_simulator.py${NC}"
    exit 1
fi

# 赋予执行权限
chmod +x gimbal_device_simulator.py

echo -e "${BLUE}正在启动云台设备模拟器...${NC}"
echo "按 Ctrl+C 停止"
echo ""

# 启动云台模拟器
python3 gimbal_device_simulator.py \
    --host "$HOST" \
    --port "$PORT" \
    --device-id "$DEVICE_ID" \
    --log-level "$LOG_LEVEL"

echo ""
echo -e "${GREEN}云台设备模拟器已退出${NC}"