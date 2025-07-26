@echo off
echo 正在安装依赖...
pip install paho-mqtt==1.6.1

echo.
echo 检查Python模块...
python -c "import paho.mqtt.client; print('✅ paho-mqtt 安装成功')"

echo.
echo 启动云台设备模拟器...
python gimbal_device_simulator_fixed.py --host 127.0.0.1 --port 1883

pause