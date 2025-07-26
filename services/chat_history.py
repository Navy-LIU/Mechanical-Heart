"""
聊天历史组件
管理消息存储、查询和持久化，使用SQLite数据库
"""
import sqlite3
import os
import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager
import threading

from models.message import Message, create_system_message

# 配置日志
logger = logging.getLogger(__name__)


class ChatHistory:
    """聊天历史管理器"""
    
    def __init__(self, db_path: str = None):
        """
        初始化聊天历史管理器
        
        Args:
            db_path: 数据库文件路径，默认为chat_history.db
        """
        self.db_path = db_path or os.path.join(os.getcwd(), 'chat_history.db')
        self._lock = threading.RLock()
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 创建消息表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        username TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        message_type TEXT NOT NULL CHECK (message_type IN ('user', 'ai', 'system')),
                        mentions_ai BOOLEAN NOT NULL DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_username ON messages(username)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(message_type)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_mentions_ai ON messages(mentions_ai)')
                
                # 创建用户会话表（用于统计）
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        session_id TEXT PRIMARY KEY,
                        username TEXT NOT NULL,
                        join_time DATETIME NOT NULL,
                        leave_time DATETIME,
                        message_count INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建用户会话表索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_sessions_username ON user_sessions(username)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_sessions_join_time ON user_sessions(join_time)')
                
                # 创建聊天统计表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS chat_statistics (
                        date DATE PRIMARY KEY,
                        total_messages INTEGER DEFAULT 0,
                        user_messages INTEGER DEFAULT 0,
                        ai_messages INTEGER DEFAULT 0,
                        system_messages INTEGER DEFAULT 0,
                        unique_users INTEGER DEFAULT 0,
                        ai_mentions INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info(f"数据库初始化完成: {self.db_path}")
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def add_message(self, message: Message) -> bool:
        """
        添加消息到历史记录
        
        Args:
            message: 消息对象
            
        Returns:
            是否添加成功
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO messages 
                        (id, content, username, timestamp, message_type, mentions_ai)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        message.id,
                        message.content,
                        message.username,
                        message.timestamp.isoformat(),
                        message.message_type,
                        message.mentions_ai
                    ))
                    
                    conn.commit()
                    
                    # 更新统计信息
                    self._update_statistics(message)
                    
                    logger.debug(f"消息已保存: {message.id}")
                    return True
                    
        except Exception as e:
            logger.error(f"保存消息失败: {e}")
            return False
    
    def get_recent_messages(self, limit: int = 50) -> List[Message]:
        """
        获取最近的消息
        
        Args:
            limit: 消息数量限制
            
        Returns:
            消息列表
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT * FROM messages 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (limit,))
                    
                    rows = cursor.fetchall()
                    messages = []
                    
                    for row in reversed(rows):  # 反转以获得正确的时间顺序
                        message = self._row_to_message(row)
                        if message:
                            messages.append(message)
                    
                    return messages
                    
        except Exception as e:
            logger.error(f"获取最近消息失败: {e}")
            return []
    
    def get_messages_by_user(self, username: str, limit: int = 20) -> List[Message]:
        """
        获取指定用户的消息
        
        Args:
            username: 用户名
            limit: 消息数量限制
            
        Returns:
            消息列表
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT * FROM messages 
                        WHERE username = ? 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (username, limit))
                    
                    rows = cursor.fetchall()
                    messages = []
                    
                    for row in reversed(rows):
                        message = self._row_to_message(row)
                        if message:
                            messages.append(message)
                    
                    return messages
                    
        except Exception as e:
            logger.error(f"获取用户消息失败: {e}")
            return []
    
    def get_messages_by_timerange(self, start: datetime, end: datetime) -> List[Message]:
        """
        获取指定时间范围内的消息
        
        Args:
            start: 开始时间
            end: 结束时间
            
        Returns:
            消息列表
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT * FROM messages 
                        WHERE timestamp BETWEEN ? AND ? 
                        ORDER BY timestamp ASC
                    ''', (start.isoformat(), end.isoformat()))
                    
                    rows = cursor.fetchall()
                    messages = []
                    
                    for row in rows:
                        message = self._row_to_message(row)
                        if message:
                            messages.append(message)
                    
                    return messages
                    
        except Exception as e:
            logger.error(f"获取时间范围消息失败: {e}")
            return []
    
    def get_ai_mentioned_messages(self, limit: int = 10) -> List[Message]:
        """
        获取提及AI的消息
        
        Args:
            limit: 消息数量限制
            
        Returns:
            消息列表
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT * FROM messages 
                        WHERE mentions_ai = 1 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (limit,))
                    
                    rows = cursor.fetchall()
                    messages = []
                    
                    for row in reversed(rows):
                        message = self._row_to_message(row)
                        if message:
                            messages.append(message)
                    
                    return messages
                    
        except Exception as e:
            logger.error(f"获取AI提及消息失败: {e}")
            return []
    
    def search_messages(self, keyword: str, limit: int = 20) -> List[Message]:
        """
        搜索包含关键词的消息
        
        Args:
            keyword: 搜索关键词
            limit: 结果数量限制
            
        Returns:
            消息列表
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT * FROM messages 
                        WHERE content LIKE ? 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (f'%{keyword}%', limit))
                    
                    rows = cursor.fetchall()
                    messages = []
                    
                    for row in reversed(rows):
                        message = self._row_to_message(row)
                        if message:
                            messages.append(message)
                    
                    return messages
                    
        except Exception as e:
            logger.error(f"搜索消息失败: {e}")
            return []
    
    def get_message_count(self) -> int:
        """获取消息总数"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT COUNT(*) FROM messages')
                    return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"获取消息总数失败: {e}")
            return 0
    
    def get_user_message_count(self, username: str) -> int:
        """获取指定用户的消息数量"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT COUNT(*) FROM messages WHERE username = ?', (username,))
                    return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"获取用户消息数量失败: {e}")
            return 0
    
    def clear_history(self, before_date: datetime = None) -> int:
        """
        清空消息历史
        
        Args:
            before_date: 清空指定日期之前的消息，None表示清空所有
            
        Returns:
            删除的消息数量
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    if before_date:
                        cursor.execute('DELETE FROM messages WHERE timestamp < ?', (before_date.isoformat(),))
                    else:
                        cursor.execute('DELETE FROM messages')
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    
                    logger.info(f"清空了 {deleted_count} 条消息")
                    return deleted_count
                    
        except Exception as e:
            logger.error(f"清空消息历史失败: {e}")
            return 0
    
    def get_chat_statistics(self) -> Dict[str, Any]:
        """获取聊天统计信息"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # 总消息数
                    cursor.execute('SELECT COUNT(*) FROM messages')
                    total_messages = cursor.fetchone()[0]
                    
                    # 各类型消息数
                    cursor.execute('''
                        SELECT message_type, COUNT(*) 
                        FROM messages 
                        GROUP BY message_type
                    ''')
                    type_counts = dict(cursor.fetchall())
                    
                    # AI提及数
                    cursor.execute('SELECT COUNT(*) FROM messages WHERE mentions_ai = 1')
                    ai_mentions = cursor.fetchone()[0]
                    
                    # 今日消息数
                    today = datetime.now().date()
                    cursor.execute('''
                        SELECT COUNT(*) FROM messages 
                        WHERE DATE(timestamp) = ?
                    ''', (today,))
                    today_messages = cursor.fetchone()[0]
                    
                    # 活跃用户数（今日发过消息的用户）
                    cursor.execute('''
                        SELECT COUNT(DISTINCT username) FROM messages 
                        WHERE DATE(timestamp) = ? AND message_type = 'user'
                    ''', (today,))
                    active_users = cursor.fetchone()[0]
                    
                    return {
                        'total_messages': total_messages,
                        'user_messages': type_counts.get('user', 0),
                        'ai_messages': type_counts.get('ai', 0),
                        'system_messages': type_counts.get('system', 0),
                        'ai_mentions': ai_mentions,
                        'today_messages': today_messages,
                        'active_users_today': active_users
                    }
                    
        except Exception as e:
            logger.error(f"获取聊天统计失败: {e}")
            return {}
    
    def backup_to_json(self, filepath: str, start_date: datetime = None, end_date: datetime = None) -> bool:
        """
        备份消息到JSON文件
        
        Args:
            filepath: 备份文件路径
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            是否备份成功
        """
        try:
            if start_date and end_date:
                messages = self.get_messages_by_timerange(start_date, end_date)
            else:
                messages = self.get_recent_messages(limit=10000)  # 获取大量消息
            
            backup_data = {
                'backup_time': datetime.now().isoformat(),
                'message_count': len(messages),
                'messages': [msg.to_dict() for msg in messages]
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"消息备份完成: {filepath}, 共 {len(messages)} 条消息")
            return True
            
        except Exception as e:
            logger.error(f"消息备份失败: {e}")
            return False
    
    def restore_from_json(self, filepath: str) -> int:
        """
        从JSON文件恢复消息
        
        Args:
            filepath: 备份文件路径
            
        Returns:
            恢复的消息数量
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            messages_data = backup_data.get('messages', [])
            restored_count = 0
            
            for msg_data in messages_data:
                try:
                    # 重建消息对象
                    message = Message(
                        id=msg_data['id'],
                        content=msg_data['content'],
                        username=msg_data['username'],
                        timestamp=datetime.fromisoformat(msg_data['timestamp']),
                        message_type=msg_data['message_type'],
                        mentions_ai=msg_data.get('mentions_ai', False)
                    )
                    
                    if self.add_message(message):
                        restored_count += 1
                        
                except Exception as e:
                    logger.warning(f"恢复消息失败: {e}")
                    continue
            
            logger.info(f"消息恢复完成: 共恢复 {restored_count} 条消息")
            return restored_count
            
        except Exception as e:
            logger.error(f"消息恢复失败: {e}")
            return 0
    
    def _row_to_message(self, row) -> Optional[Message]:
        """将数据库行转换为Message对象"""
        try:
            return Message(
                id=row['id'],
                content=row['content'],
                username=row['username'],
                timestamp=datetime.fromisoformat(row['timestamp']),
                message_type=row['message_type'],
                mentions_ai=bool(row['mentions_ai'])
            )
        except Exception as e:
            logger.error(f"转换消息对象失败: {e}")
            return None
    
    def _update_statistics(self, message: Message):
        """更新统计信息"""
        try:
            today = datetime.now().date()
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取或创建今日统计记录
                cursor.execute('SELECT * FROM chat_statistics WHERE date = ?', (today,))
                stats = cursor.fetchone()
                
                if stats:
                    # 将Row对象转换为字典
                    stats = dict(stats)
                    # 更新现有记录
                    updates = {
                        'total_messages': stats['total_messages'] + 1
                    }
                    
                    if message.message_type == 'user':
                        updates['user_messages'] = stats['user_messages'] + 1
                    elif message.message_type == 'ai':
                        updates['ai_messages'] = stats['ai_messages'] + 1
                    elif message.message_type == 'system':
                        updates['system_messages'] = stats['system_messages'] + 1
                    
                    if message.mentions_ai:
                        updates['ai_mentions'] = stats.get('ai_mentions', 0) + 1
                    else:
                        updates['ai_mentions'] = stats.get('ai_mentions', 0)
                    
                    cursor.execute('''
                        UPDATE chat_statistics 
                        SET total_messages = ?, user_messages = ?, ai_messages = ?, 
                            system_messages = ?, ai_mentions = ?
                        WHERE date = ?
                    ''', (
                        updates['total_messages'],
                        updates.get('user_messages', stats.get('user_messages', 0)),
                        updates.get('ai_messages', stats.get('ai_messages', 0)),
                        updates.get('system_messages', stats.get('system_messages', 0)),
                        updates['ai_mentions'],
                        today
                    ))
                else:
                    # 创建新记录
                    cursor.execute('''
                        INSERT INTO chat_statistics 
                        (date, total_messages, user_messages, ai_messages, system_messages, ai_mentions)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        today,
                        1,
                        1 if message.message_type == 'user' else 0,
                        1 if message.message_type == 'ai' else 0,
                        1 if message.message_type == 'system' else 0,
                        1 if message.mentions_ai else 0
                    ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"更新统计信息失败: {e}")
    
    def close(self):
        """关闭数据库连接（清理资源）"""
        # SQLite连接在上下文管理器中自动关闭，这里主要用于日志
        logger.info("聊天历史管理器已关闭")
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"ChatHistory(db={self.db_path}, messages={self.get_message_count()})"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"ChatHistory(db_path='{self.db_path}', message_count={self.get_message_count()})"


class ChatHistoryManager:
    """聊天历史管理器（单例模式）"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.chat_history = ChatHistory()
            self._initialized = True
    
    def get_chat_history(self) -> ChatHistory:
        """获取聊天历史实例"""
        return self.chat_history
    
    def reset_chat_history(self, db_path: str = None):
        """重置聊天历史（用于测试）"""
        if hasattr(self, 'chat_history'):
            self.chat_history.close()
        self.chat_history = ChatHistory(db_path)
    
    @classmethod
    def get_instance(cls) -> 'ChatHistoryManager':
        """获取管理器实例"""
        return cls()


def get_chat_history() -> ChatHistory:
    """获取全局聊天历史实例的便捷函数"""
    return ChatHistoryManager.get_instance().get_chat_history()