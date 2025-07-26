"""
AI聊天室主应用入口
集成Flask和SocketIO实现实时多用户聊天功能
"""
import os
import logging
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, disconnect
from dotenv import load_dotenv

from services.websocket_handler import WebSocketHandler
from services.broadcast_manager import SocketIOBroadcastAdapter

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# 创建SocketIO实例
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
    async_mode='eventlet'
)

# 创建WebSocket处理器和广播适配器
websocket_handler = WebSocketHandler()
broadcast_adapter = SocketIOBroadcastAdapter(socketio)

@app.route('/')
def index():
    """聊天室主页面"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """健康检查端点"""
    return {
        'status': 'healthy',
        'service': 'ai-chat-room',
        'version': '1.0.0'
    }

# WebSocket事件处理
@socketio.on('connect')
def handle_connect():
    """处理客户端连接"""
    try:
        client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
        user_agent = request.headers.get('User-Agent', 'unknown')
        
        logger.info(f"客户端连接: {request.sid}, IP: {client_ip}")
        
        # 使用WebSocket处理器处理连接
        result = websocket_handler.handle_connect(
            socket_id=request.sid,
            client_info={
                'ip': client_ip,
                'user_agent': user_agent,
                'connect_time': None  # 将在处理器中设置
            }
        )
        
        if result['success']:
            # 发送连接成功消息
            emit('connect_success', {
                'message': '连接成功',
                'socket_id': request.sid,
                'server_time': result['server_time']
            })
            
            logger.info(f"连接处理成功: {request.sid}")
        else:
            # 连接失败，断开连接
            logger.warning(f"连接处理失败: {request.sid}, {result['error']}")
            emit('connect_error', {'error': result['error']})
            disconnect()
            
    except Exception as e:
        logger.error(f"连接处理异常: {request.sid}, {e}")
        emit('connect_error', {'error': '服务器内部错误'})
        disconnect()

@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接"""
    try:
        logger.info(f"客户端断开连接: {request.sid}")
        
        # 使用WebSocket处理器处理断开
        result = websocket_handler.handle_disconnect(request.sid)
        
        if result['success']:
            logger.info(f"断开连接处理成功: {request.sid}")
        else:
            logger.warning(f"断开连接处理失败: {request.sid}, {result['error']}")
            
    except Exception as e:
        logger.error(f"断开连接处理异常: {request.sid}, {e}")

@socketio.on('ping')
def handle_ping():
    """处理心跳检测"""
    try:
        result = websocket_handler.handle_ping(request.sid)
        
        if result['success']:
            emit('pong', {
                'timestamp': result['timestamp'],
                'server_time': result['server_time']
            })
        else:
            emit('ping_error', {'error': result['error']})
            
    except Exception as e:
        logger.error(f"心跳处理异常: {request.sid}, {e}")
        emit('ping_error', {'error': '心跳处理失败'})

@socketio.on('get_server_info')
def handle_get_server_info():
    """获取服务器信息"""
    try:
        info = websocket_handler.get_server_info()
        emit('server_info', info)
        
    except Exception as e:
        logger.error(f"获取服务器信息异常: {request.sid}, {e}")
        emit('server_info_error', {'error': '获取服务器信息失败'})

@socketio.on('get_connection_stats')
def handle_get_connection_stats():
    """获取连接统计信息"""
    try:
        stats = websocket_handler.get_connection_stats()
        emit('connection_stats', stats)
        
    except Exception as e:
        logger.error(f"获取连接统计异常: {request.sid}, {e}")
        emit('connection_stats_error', {'error': '获取统计信息失败'})

@socketio.on_error_default
def default_error_handler(e):
    """默认错误处理器"""
    logger.error(f"WebSocket错误: {request.sid}, {e}")
    
    # 记录错误到WebSocket处理器
    websocket_handler.handle_error(request.sid, str(e))
    
    # 发送错误通知给客户端
    emit('error', {
        'message': '发生了一个错误',
        'error_id': request.sid,
        'timestamp': websocket_handler._get_current_time()
    })

# 错误处理
@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    logger.error(f"内部服务器错误: {error}")
    return render_template('500.html'), 500

if __name__ == '__main__':
    # 开发环境配置
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    
    logger.info(f"启动AI聊天室服务器...")
    logger.info(f"访问地址: http://localhost:{port}")
    logger.info(f"调试模式: {debug_mode}")
    
    try:
        socketio.run(
            app, 
            debug=debug_mode, 
            host=host, 
            port=port,
            use_reloader=debug_mode,
            log_output=debug_mode
        )
    except KeyboardInterrupt:
        logger.info("服务器已停止")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        raise