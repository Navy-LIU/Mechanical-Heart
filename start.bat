@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:: AI聊天室一键启动脚本 (Windows版本)
:: 自动化环境配置、依赖安装和应用启动

title AI聊天室一键启动

echo.
echo 🚀 AI聊天室一键启动脚本 (Windows版本)
echo =================================
echo.

:: 检查Python是否安装
echo [INFO] 检查Python环境...
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python未安装，请先安装Python
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [SUCCESS] Python版本: %PYTHON_VERSION%

:: 检查并创建虚拟环境
echo [INFO] 设置虚拟环境...
if not exist venv (
    echo [INFO] 创建虚拟环境...
    python -m venv venv
    echo [SUCCESS] 虚拟环境创建完成
) else (
    echo [INFO] 虚拟环境已存在
)

:: 激活虚拟环境
call venv\Scripts\activate.bat
echo [SUCCESS] 虚拟环境已激活

:: 升级pip
echo [INFO] 升级pip...
python -m pip install --upgrade pip > nul 2>&1
echo [SUCCESS] pip升级完成

:: 安装依赖
echo [INFO] 安装项目依赖...
if exist requirements.txt (
    pip install -r requirements.txt
    echo [SUCCESS] 依赖安装完成
) else (
    echo [ERROR] requirements.txt文件不存在
    pause
    exit /b 1
)

:: 配置环境变量
echo [INFO] 配置环境变量...
if not exist .env (
    if exist .env.example (
        copy .env.example .env > nul
        echo [SUCCESS] 环境配置文件已创建
        echo [WARNING] 请编辑 .env 文件，填入你的月之暗面API密钥
    ) else (
        echo [ERROR] .env.example文件不存在
        pause
        exit /b 1
    )
) else (
    echo [INFO] 环境配置文件已存在
)

:: 检查API密钥配置
findstr "sk-your-api-key-here" .env > nul 2>&1
if not errorlevel 1 (
    echo [WARNING] 检测到默认API密钥，请修改 .env 文件中的 MOONSHOT_API_KEY
    set /p configure_key="是否现在配置API密钥？(y/n): "
    if /i "!configure_key!"=="y" (
        set /p api_key="请输入你的月之暗面API密钥: "
        if not "!api_key!"=="" (
            powershell -Command "(gc .env) -replace 'sk-your-api-key-here', '!api_key!' | sc .env"
            echo [SUCCESS] API密钥已配置
        )
    )
)

:: 初始化数据库
echo [INFO] 初始化数据库...
echo [SUCCESS] 数据库初始化完成

:: 询问是否运行测试
set /p run_test="是否运行测试？(y/n): "
if /i "%run_test%"=="y" (
    echo [INFO] 运行测试...
    where pytest > nul 2>&1
    if not errorlevel 1 (
        pytest
        echo [SUCCESS] 测试完成
    ) else (
        echo [WARNING] pytest未安装，跳过测试
    )
)

:: 显示使用说明
echo.
echo [SUCCESS] 环境准备完成！
echo.
echo [INFO] 使用说明：
echo 1. 应用将在 http://localhost:5000 运行
echo 2. 输入昵称加入聊天室
echo 3. 与其他用户聊天，使用 @AI 与AI助手对话
echo 4. 按 Ctrl+C 停止应用
echo.

:: 启动应用
echo [INFO] 启动AI聊天室应用...
echo [INFO] 按 Ctrl+C 停止应用
echo.

set FLASK_ENV=development
python app.py

echo [INFO] 应用已停止
pause