#!/bin/bash

# AI聊天室一键启动脚本
# 自动化环境配置、依赖安装和应用启动

set -e  # 遇到错误立即退出

echo "🚀 AI聊天室一键启动脚本"
echo "========================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Python版本
check_python() {
    log_info "检查Python环境..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3未安装，请先安装Python3"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d" " -f2 | cut -d"." -f1-2)
    log_success "Python版本: $(python3 --version)"
    
    # 检查Python版本是否大于等于3.8
    if [ $(echo "$PYTHON_VERSION >= 3.8" | bc -l) -eq 0 ]; then
        log_warning "建议使用Python 3.8或更高版本"
    fi
}

# 检查并创建虚拟环境
setup_venv() {
    log_info "设置虚拟环境..."
    
    if [ ! -d "venv" ]; then
        log_info "创建虚拟环境..."
        python3 -m venv venv
        log_success "虚拟环境创建完成"
    else
        log_info "虚拟环境已存在"
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    log_success "虚拟环境已激活"
    
    # 升级pip
    log_info "升级pip..."
    pip install --upgrade pip > /dev/null 2>&1
    log_success "pip升级完成"
}

# 安装依赖
install_dependencies() {
    log_info "安装项目依赖..."
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        log_success "依赖安装完成"
    else
        log_error "requirements.txt文件不存在"
        exit 1
    fi
}

# 配置环境变量
setup_env() {
    log_info "配置环境变量..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_success "环境配置文件已创建"
            log_warning "请编辑 .env 文件，填入你的月之暗面API密钥"
            log_warning "编辑命令: nano .env 或 vim .env"
        else
            log_error ".env.example文件不存在"
            exit 1
        fi
    else
        log_info "环境配置文件已存在"
    fi
    
    # 检查API密钥配置
    if grep -q "sk-your-api-key-here" .env; then
        log_warning "检测到默认API密钥，请修改 .env 文件中的 MOONSHOT_API_KEY"
        read -p "是否现在配置API密钥？(y/n): " configure_key
        if [ "$configure_key" = "y" ] || [ "$configure_key" = "Y" ]; then
            read -p "请输入你的月之暗面API密钥: " api_key
            if [ ! -z "$api_key" ]; then
                sed -i "s/sk-your-api-key-here/$api_key/g" .env
                log_success "API密钥已配置"
            fi
        fi
    fi
}

# 运行数据库初始化（如果需要）
init_database() {
    log_info "初始化数据库..."
    # 由于使用SQLite，会自动创建数据库文件，无需额外初始化
    log_success "数据库初始化完成"
}

# 运行测试（可选）
run_tests() {
    read -p "是否运行测试？(y/n): " run_test
    if [ "$run_test" = "y" ] || [ "$run_test" = "Y" ]; then
        log_info "运行测试..."
        if command -v pytest &> /dev/null; then
            pytest
            log_success "测试完成"
        else
            log_warning "pytest未安装，跳过测试"
        fi
    fi
}

# 启动应用
start_app() {
    log_info "启动AI聊天室应用..."
    log_info "应用将在 http://localhost:5000 运行"
    log_info "按 Ctrl+C 停止应用"
    echo ""
    
    # 导出环境变量
    export FLASK_ENV=development
    
    # 启动应用
    python app.py
}

# 显示使用说明
show_usage() {
    echo ""
    log_info "使用说明："
    echo "1. 打开浏览器访问 http://localhost:5000"
    echo "2. 输入昵称加入聊天室"
    echo "3. 与其他用户聊天，使用 @AI 与AI助手对话"
    echo "4. 按 Ctrl+C 停止应用"
    echo ""
}

# 清理函数
cleanup() {
    log_info "正在停止应用..."
    log_success "应用已停止"
}

# 注册清理函数
trap cleanup EXIT

# 主函数
main() {
    echo ""
    log_info "开始一键启动流程..."
    echo ""
    
    # 检查Python环境
    check_python
    
    # 设置虚拟环境
    setup_venv
    
    # 安装依赖
    install_dependencies
    
    # 配置环境变量
    setup_env
    
    # 初始化数据库
    init_database
    
    # 运行测试（可选）
    run_tests
    
    echo ""
    log_success "环境准备完成！"
    show_usage
    
    # 启动应用
    start_app
}

# 运行主函数
main