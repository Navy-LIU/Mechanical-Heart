"""
AI聊天室主应用入口
集成Flask和SocketIO实现实时多用户聊天功能
"""
import os
import logging
from datetime import datetime
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
    logger=False,
    engineio_logger=False,
    async_mode='threading'
)

# 创建WebSocket处理器和广播适配器
broadcast_adapter = SocketIOBroadcastAdapter(socketio)
websocket_handler = WebSocketHandler(broadcast_adapter=broadcast_adapter)

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

# 聊天室相关事件处理
@socketio.on('join_room')
def handle_join_room(data):
    """处理用户加入聊天室"""
    try:
        logger.info(f"用户请求加入聊天室: {request.sid}, data: {data}")
        
        result = websocket_handler.handle_join_room(request.sid, data)
        
        if result['success']:
            # 发送成功响应给当前用户
            emit('join_room_success', {
                'message': result['message'],
                'user': result['user'],
                'session_id': result['session_id'],
                'chat_history': result['chat_history'],
                'online_users': result['online_users'],
                'server_time': result['server_time']
            })
            
            logger.info(f"用户加入聊天室成功: {result['user']['username']}")
        else:
            # 发送错误响应
            emit('join_room_error', {'error': result['error']})
            logger.warning(f"用户加入聊天室失败: {request.sid}, {result['error']}")
            
    except Exception as e:
        logger.error(f"加入聊天室处理异常: {request.sid}, {e}")
        emit('join_room_error', {'error': '加入聊天室时发生服务器错误'})

@socketio.on('send_message')
def handle_send_message(data):
    """处理发送消息"""
    try:
        logger.info(f"收到消息: {request.sid}, data: {data}")
        
        result = websocket_handler.handle_send_message(request.sid, data)
        
        if result['success']:
            # 发送成功确认给发送者
            emit('message_sent', {
                'message': result['message'],
                'message_data': result['message_data'],
                'ai_response': result['ai_response']
            })
            
            logger.info(f"消息发送成功: {request.sid}")
        else:
            # 发送错误响应
            emit('message_error', {'error': result['error']})
            logger.warning(f"消息发送失败: {request.sid}, {result['error']}")
            
    except Exception as e:
        logger.error(f"发送消息处理异常: {request.sid}, {e}")
        emit('message_error', {'error': '发送消息时发生服务器错误'})

@socketio.on('get_chat_history')
def handle_get_chat_history(data):
    """获取聊天历史"""
    try:
        limit = data.get('limit', 50) if data else 50
        
        # 获取聊天历史
        from services.chat_history import get_chat_history
        chat_history = get_chat_history()
        recent_messages = chat_history.get_recent_messages(limit=limit)
        
        history_data = []
        for msg in recent_messages:
            history_data.append({
                'type': 'message',
                'username': msg.username,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat(),
                'is_ai': msg.message_type == 'ai',
                'is_system': msg.message_type == 'system',
                'message_id': msg.id
            })
        
        emit('chat_history', {
            'messages': history_data,
            'total_count': len(history_data)
        })
        
    except Exception as e:
        logger.error(f"获取聊天历史异常: {request.sid}, {e}")
        emit('chat_history_error', {'error': '获取聊天历史失败'})

@socketio.on('get_online_users')
def handle_get_online_users():
    """获取在线用户列表"""
    try:
        online_users = websocket_handler.user_manager.get_online_users()
        total_users = websocket_handler.user_manager.get_online_user_count()
        
        emit('online_users', {
            'users': online_users,
            'total_users': total_users,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取在线用户异常: {request.sid}, {e}")
        emit('online_users_error', {'error': '获取在线用户失败'})

@socketio.on('update_display_name')
def handle_update_display_name(data):
    """处理更新用户显示名称"""
    try:
        logger.info(f"用户请求更新显示名称: {request.sid}, data: {data}")
        
        # 获取用户信息
        user = websocket_handler.user_manager.get_user_by_socket(request.sid)
        if not user:
            emit('update_display_name_error', {'error': '用户未找到，请重新加入聊天室'})
            return
        
        new_display_name = data.get('display_name', '').strip()
        if not new_display_name:
            emit('update_display_name_error', {'error': '显示名称不能为空'})
            return
        
        # 更新显示名称
        success, message = websocket_handler.user_manager.update_user_display_name(
            user.session_id, new_display_name
        )
        
        if success:
            # 发送成功响应
            emit('update_display_name_success', {
                'message': message,
                'new_display_name': new_display_name,
                'user_info': user.to_dict()
            })
            
            # 广播用户列表更新
            from services.broadcast_manager import get_broadcast_manager
            broadcast_manager = get_broadcast_manager()
            broadcast_manager.broadcast_user_list_update(
                users=websocket_handler.user_manager.get_online_users(),
                user_count=websocket_handler.user_manager.get_online_user_count(),
                room="main"
            )
            
            logger.info(f"用户显示名称更新成功: {user.username} -> {new_display_name}")
        else:
            emit('update_display_name_error', {'error': message})
            logger.warning(f"显示名称更新失败: {request.sid}, {message}")
            
    except Exception as e:
        logger.error(f"更新显示名称异常: {request.sid}, {e}")
        emit('update_display_name_error', {'error': '更新显示名称时发生服务器错误'})

@socketio.on('get_user_info')
def handle_get_user_info():
    """获取当前用户信息"""
    try:
        user = websocket_handler.user_manager.get_user_by_socket(request.sid)
        if not user:
            emit('user_info_error', {'error': '用户未找到'})
            return
        
        # 获取详细用户信息
        user_info = websocket_handler.user_manager.get_user_display_info(user.session_id)
        
        emit('user_info', {
            'user': user_info,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取用户信息异常: {request.sid}, {e}")
        emit('user_info_error', {'error': '获取用户信息失败'})

@socketio.on_error_default
def default_error_handler(e):
    """默认错误处理器"""
    logger.error(f"WebSocket错误: {request.sid}, {e}")
    
    # 发送错误通知给客户端
    emit('error', {
        'message': '发生了一个错误',
        'error_id': request.sid,
        'timestamp': datetime.now().isoformat()
    })

# HTTP错误处理
@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return {'error': '页面未找到'}, 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    logger.error(f"内部服务器错误: {error}")
    return {'error': '内部服务器错误'}, 500

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
            log_output=debug_mode,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        logger.info("服务器已停止")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        raise