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
from services.mqtt_service import get_mqtt_service, start_mqtt_service, stop_mqtt_service
from services.message_handler import get_message_handler
import urllib.parse
import uuid

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

# MQTT配置
mqtt_enabled = os.getenv('MQTT_ENABLE', 'false').lower() == 'true'
mqtt_broker = os.getenv('MQTT_BROKER', 'localhost')
mqtt_port = int(os.getenv('MQTT_PORT', 1883))

# 启动MQTT服务（如果启用）
if mqtt_enabled:
    logger.info(f"正在启动MQTT服务: {mqtt_broker}:{mqtt_port}")
    mqtt_success = start_mqtt_service(mqtt_broker, mqtt_port)
    if mqtt_success:
        logger.info("MQTT服务启动成功")
    else:
        logger.warning("MQTT服务启动失败，将继续运行但不支持MQTT功能")
else:
    logger.info("MQTT服务已禁用")

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

@app.route('/quick-send')
def quick_send_get():
    """
    URL快速发送消息 (GET)
    参数:
        username: 用户名
        message: 消息内容
    示例: /quick-send?username=test&message=hello
    """
    try:
        # 获取参数
        username = request.args.get('username', '').strip()
        message = request.args.get('message', '').strip()
        
        if not username or not message:
            return {
                'success': False,
                'error': '缺少参数: username 和 message 都是必需的',
                'usage': '/quick-send?username=用户名&message=消息内容'
            }, 400
        
        # URL解码
        username = urllib.parse.unquote(username)
        message = urllib.parse.unquote(message)
        
        # 验证参数
        if len(username) > 20:
            return {'success': False, 'error': '用户名不能超过20个字符'}, 400
        
        if len(message) > 1000:
            return {'success': False, 'error': '消息内容不能超过1000个字符'}, 400
        
        # 处理消息
        result = _process_url_message(username, message)
        
        return {
            'success': result['success'],
            'message': result['message'],
            'timestamp': datetime.now().isoformat(),
            'user_info': result.get('user_info'),
            'ai_response': result.get('ai_response')
        }
        
    except Exception as e:
        logger.error(f"URL快速发送异常: {e}")
        return {
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }, 500

@app.route('/quick-send', methods=['POST'])
def quick_send_post():
    """
    URL快速发送消息 (POST)
    JSON参数:
        {
            "username": "用户名",
            "message": "消息内容",
            "display_name": "显示名称" (可选)
        }
    """
    try:
        data = request.get_json()
        if not data:
            return {
                'success': False,
                'error': '请提供JSON数据'
            }, 400
        
        username = data.get('username', '').strip()
        message = data.get('message', '').strip()
        display_name = data.get('display_name', '').strip()
        
        if not username or not message:
            return {
                'success': False,
                'error': 'username 和 message 字段都是必需的'
            }, 400
        
        # 验证参数
        if len(username) > 20:
            return {'success': False, 'error': '用户名不能超过20个字符'}, 400
        
        if len(message) > 1000:
            return {'success': False, 'error': '消息内容不能超过1000个字符'}, 400
        
        # 处理消息
        result = _process_url_message(username, message, display_name)
        
        return {
            'success': result['success'],
            'message': result['message'],
            'timestamp': datetime.now().isoformat(),
            'user_info': result.get('user_info'),
            'ai_response': result.get('ai_response')
        }
        
    except Exception as e:
        logger.error(f"URL快速发送异常: {e}")
        return {
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }, 500

def _process_url_message(username: str, message: str, display_name: str = None) -> dict:
    """
    处理URL消息发送
    
    Args:
        username: 用户名
        message: 消息内容
        display_name: 显示名称
    
    Returns:
        处理结果
    """
    try:
        # 生成临时会话
        session_id = f"url_{str(uuid.uuid4())[:8]}"
        
        # 获取消息处理器
        message_handler = get_message_handler()
        
        # 添加URL标识
        final_username = f"{username} (URL)"
        
        # 处理消息
        result = message_handler.process_message(
            message_content=message,
            username=final_username,
            session_id=session_id
        )
        
        if result['success']:
            # 广播消息到所有客户端
            websocket_handler.broadcast_manager.broadcast_message(
                message=result['message'],
                ai_response=result['ai_response'],
                room="main"
            )
            
            # 发送到MQTT服务（如果可用）
            try:
                mqtt_service = get_mqtt_service()
                if mqtt_service.is_connected:
                    mqtt_service.send_message_to_mqtt(result['message'], result['ai_response'])
            except Exception as e:
                logger.warning(f"MQTT发送失败: {e}")
            
            return {
                'success': True,
                'message': '消息发送成功',
                'user_info': {
                    'username': final_username,
                    'display_name': display_name or username,
                    'session_id': session_id,
                    'message_id': result['message'].id
                },
                'ai_response': result['ai_response'].to_dict() if result['ai_response'] else None
            }
        else:
            return {
                'success': False,
                'message': result['error']
            }
    
    except Exception as e:
        logger.error(f"处理URL消息异常: {e}")
        return {
            'success': False,
            'message': f'处理消息失败: {str(e)}'
        }

@app.route('/mqtt/status')
def mqtt_status():
    """获取MQTT服务状态"""
    try:
        mqtt_service = get_mqtt_service()
        stats = mqtt_service.get_statistics()
        
        return {
            'success': True,
            'mqtt_status': stats,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"获取MQTT状态异常: {e}")
        return {
            'success': False,
            'error': f'获取MQTT状态失败: {str(e)}'
        }, 500

@app.route('/api/gimbal/control', methods=['POST'])
def gimbal_control_api():
    """
    云台控制API端点
    接受JSON数据: {"x": 2500, "y": 2000, "username": "API用户"}
    """
    try:
        data = request.get_json()
        if not data:
            return {
                'success': False,
                'error': '请提供JSON数据'
            }, 400
        
        x = data.get('x')
        y = data.get('y')
        username = data.get('username', 'API_User')
        
        # 参数验证
        if x is None or y is None:
            return {
                'success': False,
                'error': '缺少必需参数: x 和 y'
            }, 400
        
        try:
            x = int(x)
            y = int(y)
        except (ValueError, TypeError):
            return {
                'success': False,
                'error': '参数 x 和 y 必须是整数'
            }, 400
        
        # 验证参数范围
        if not (1024 <= x <= 3048):
            return {
                'success': False,
                'error': f'参数 x 超出范围: {x}，应在1024-3048之间'
            }, 400
        
        if not (1850 <= y <= 2400):
            return {
                'success': False,
                'error': f'参数 y 超出范围: {y}，应在1850-2400之间'
            }, 400
        
        # 获取MQTT服务并发送控制指令
        mqtt_service = get_mqtt_service()
        if not mqtt_service or not mqtt_service.is_connected:
            return {
                'success': False,
                'error': 'MQTT服务不可用'
            }, 503
        
        success = mqtt_service.send_gimbal_command_from_chat(x, y, username)
        
        if success:
            return {
                'success': True,
                'message': f'云台控制指令已发送: X={x}, Y={y}',
                'control_data': {
                    'x': x,
                    'y': y,
                    'username': username,
                    'timestamp': datetime.now().isoformat()
                }
            }
        else:
            return {
                'success': False,
                'error': '发送云台控制指令失败'
            }, 500
            
    except Exception as e:
        logger.error(f"云台控制API异常: {e}")
        return {
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }, 500

@app.route('/api/gimbal/status')
def gimbal_status_api():
    """
    获取云台状态API端点
    返回所有已连接云台设备的状态信息
    """
    try:
        mqtt_service = get_mqtt_service()
        if not mqtt_service or not mqtt_service.is_connected:
            return {
                'success': False,
                'error': 'MQTT服务不可用',
                'gimbals': []
            }, 503
        
        # 获取云台状态信息
        gimbal_status = mqtt_service.get_gimbal_status()
        
        return {
            'success': True,
            'message': '云台状态获取成功',
            'gimbals': gimbal_status,
            'total_count': len(gimbal_status),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"云台状态API异常: {e}")
        return {
            'success': False,
            'error': f'服务器错误: {str(e)}',
            'gimbals': []
        }, 500

@app.route('/api/gimbal/list')
def gimbal_list_api():
    """
    获取云台设备列表API端点
    返回所有已注册的云台设备信息
    """
    try:
        mqtt_service = get_mqtt_service()
        if not mqtt_service or not mqtt_service.is_connected:
            return {
                'success': False,
                'error': 'MQTT服务不可用',
                'devices': []
            }, 503
        
        # 获取云台设备列表
        gimbal_devices = mqtt_service.get_gimbal_devices()
        
        return {
            'success': True,
            'message': '云台设备列表获取成功',
            'devices': gimbal_devices,
            'total_count': len(gimbal_devices),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"云台设备列表API异常: {e}")
        return {
            'success': False,
            'error': f'服务器错误: {str(e)}',
            'devices': []
        }, 500

@app.route('/api/docs')
def api_docs():
    """
API文档
    """
    docs = {
        'service': 'AI聊天室 API',
        'version': '1.0.0',
        'endpoints': {
            'quick_send_get': {
                'method': 'GET',
                'url': '/quick-send?username=用户名&message=消息内容',
                'description': '通过URL参数快速发送消息',
                'parameters': {
                    'username': '用户名（必需，最多20个字符）',
                    'message': '消息内容（必需，最多1000个字符）'
                },
                'example': '/quick-send?username=测试用户&message=你好世界'
            },
            'quick_send_post': {
                'method': 'POST',
                'url': '/quick-send',
                'description': '通过JSON数据快速发送消息',
                'content_type': 'application/json',
                'body': {
                    'username': '用户名（必需）',
                    'message': '消息内容（必需）',
                    'display_name': '显示名称（可选）'
                }
            },
            'mqtt_status': {
                'method': 'GET',
                'url': '/mqtt/status',
                'description': '获取MQTT服务状态'
            },
            'health': {
                'method': 'GET',
                'url': '/health',
                'description': '服务健康检查'
            },
            'gimbal_control': {
                'method': 'POST',
                'url': '/api/gimbal/control',
                'description': '云台控制API',
                'content_type': 'application/json',
                'body': {
                    'x': '水平角度（必需，范围: 1024-3048）',
                    'y': '垂直角度（必需，范围: 1850-2400）',
                    'username': '操作用户（可选，默认: API_User）'
                },
                'example': '{"x": 2500, "y": 2000, "username": "测试用户"}'
            },
            'gimbal_status': {
                'method': 'GET',
                'url': '/api/gimbal/status',
                'description': '获取云台状态信息',
                'returns': '返回所有已连接云台设备的状态'
            },
            'gimbal_list': {
                'method': 'GET',
                'url': '/api/gimbal/list',
                'description': '获取云台设备列表',
                'returns': '返回所有已注册的云台设备信息'
            }
        },
        'mqtt_info': {
            'description': 'MQTT服务支持',
            'broker': '默认localhost:1883',
            'topics': {
                'chatroom/messages/in': '发送消息到聊天室',
                'chatroom/messages/out': '从聊天室接收消息',
                'chatroom/users/join': '用户加入通知',
                'chatroom/users/leave': '用户离开通知',
                'chatroom/system': '系统消息',
                'device/gimbal/control': '云台控制命令'
            },
            'message_format': {
                'type': 'JSON',
                'chat_message': {
                    'username': '用户名',
                    'message': '消息内容',
                    'client_id': 'MQTT客户端ID'
                },
                'gimbal_control': {
                    'format': 'Ang_X=xxx,Ang_Y=yyy',
                    'description': '云台控制命令格式',
                    'parameters': {
                        'Ang_X': '水平角度，范围: 1024-3048',
                        'Ang_Y': '垂直角度，范围: 1850-2400'
                    },
                    'example': 'Ang_X=2036,Ang_Y=2125'
                }
            }
        }
    }
    
    return docs

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

@socketio.on('get_username_suggestions')
def handle_get_username_suggestions():
    """获取用户名建议（针对重复访问IP）"""
    try:
        result = websocket_handler.handle_get_username_suggestions(request.sid)
        
        if result['success']:
            emit('username_suggestions', {
                'success': True,
                'data': result,
                'timestamp': datetime.now().isoformat()
            })
        else:
            emit('username_suggestions_error', {
                'success': False,
                'error': result['error'],
                'timestamp': datetime.now().isoformat()
            })
        
        logger.info(f"用户名建议请求处理完成: {request.sid}")
        
    except Exception as e:
        logger.error(f"获取用户名建议异常: {request.sid}, {e}")
        emit('username_suggestions_error', {
            'success': False,
            'error': '获取用户名建议失败',
            'timestamp': datetime.now().isoformat()
        })

@socketio.on('get_gimbal_status')
def handle_get_gimbal_status():
    """获取云台状态信息"""
    try:
        if mqtt_enabled and mqtt_service:
            # 获取MQTT服务中的云台状态
            gimbal_status = mqtt_service.get_statistics()
            emit('gimbal_status', gimbal_status)
            logger.info(f"发送云台状态: {request.sid}")
        else:
            # MQTT服务未启用或不可用时返回默认状态
            default_status = {
                'is_connected': False,
                'is_running': False,
                'broker_info': 'MQTT服务未启用',
                'mqtt_users_count': 0,
                'gimbal_devices_count': 0,
                'is_gimbal_online': False,
                'messages_received': 0,
                'messages_sent': 0,
                'gimbal_commands_sent': 0,
                'connect_time': None,
                'last_message_time': None,
                'active_topics': [],
                'mqtt_users': [],
                'gimbal_devices': []
            }
            emit('gimbal_status', default_status)
            logger.info(f"发送默认云台状态: {request.sid}")
            
    except Exception as e:
        logger.error(f"获取云台状态异常: {request.sid}, {e}")
        emit('gimbal_status_error', {
            'error': '获取云台状态失败',
            'timestamp': datetime.now().isoformat()
        })

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
    logger.info(f"URL快速发送: http://localhost:{port}/quick-send?username=用户名&message=消息")
    logger.info(f"API文档: http://localhost:{port}/api/docs")
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
        logger.info("正在停止服务器...")
        # 停止MQTT服务
        if mqtt_enabled:
            stop_mqtt_service()
            logger.info("MQTT服务已停止")
        logger.info("服务器已停止")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        # 停止MQTT服务
        if mqtt_enabled:
            stop_mqtt_service()
        raise