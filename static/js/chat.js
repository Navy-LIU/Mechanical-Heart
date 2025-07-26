// AI聊天室客户端JavaScript
class ChatClient {
    constructor() {
        this.socket = null;
        this.username = '';
        this.isConnected = false;
        this.isJoining = false;
        this.isSending = false;
        this.typingTimer = null;
        this.isTyping = false;
        
        this.initializeElements();
        this.bindEvents();
        this.showUsernameModal();
        this.setupKeyboardShortcuts();
    }
    
    initializeElements() {
        // DOM元素引用
        this.usernameModal = document.getElementById('username-modal');
        this.usernameInput = document.getElementById('username-input');
        this.usernameCounter = document.getElementById('username-counter');
        this.usernameError = document.getElementById('username-error');
        this.joinBtn = document.getElementById('join-btn');
        
        this.messageInput = document.getElementById('message-input');
        this.charCounter = document.getElementById('char-counter');
        this.sendBtn = document.getElementById('send-btn');
        this.btnText = this.sendBtn.querySelector('.btn-text');
        this.btnLoading = this.sendBtn.querySelector('.btn-loading');
        
        this.messagesContainer = document.getElementById('messages');
        this.messagesLoading = document.getElementById('messages-loading');
        this.noMessages = document.getElementById('no-messages');
        
        this.usersContainer = document.getElementById('users');
        this.usersLoading = document.getElementById('users-loading');
        this.onlineCount = document.getElementById('online-count');
        
        this.connectionIndicator = document.getElementById('connection-indicator');
        this.connectionStatus = document.getElementById('connection-status');
        this.typingIndicator = document.getElementById('typing-indicator');
        
        this.notification = document.getElementById('notification');
        this.notificationMessage = document.getElementById('notification-message');
        this.notificationClose = document.getElementById('notification-close');
    }
    
    bindEvents() {
        // 用户名模态框
        this.joinBtn.addEventListener('click', () => this.joinChat());
        this.usernameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.joinChat();
        });
        this.usernameInput.addEventListener('input', () => this.updateUsernameCounter());
        
        // 消息发送
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        this.messageInput.addEventListener('input', () => {
            this.updateCharCounter();
            this.handleTyping();
        });
        
        // 通知关闭
        this.notificationClose.addEventListener('click', () => this.hideNotification());
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+Enter 快速发送消息
            if (e.ctrlKey && e.key === 'Enter' && this.isConnected && this.usernameModal.style.display === 'none') {
                this.sendMessage();
            }
            
            // Escape 关闭通知
            if (e.key === 'Escape') {
                this.hideNotification();
            }
            
            // Alt+A 快速输入@AI
            if (e.altKey && e.key === 'a' && this.isConnected && this.usernameModal.style.display === 'none') {
                e.preventDefault();
                const currentValue = this.messageInput.value;
                if (!currentValue.includes('@AI')) {
                    this.messageInput.value = '@AI ' + currentValue;
                    this.messageInput.focus();
                    this.messageInput.setSelectionRange(4, 4); // 将光标移动到@AI之后
                    this.updateCharCounter();
                }
            }
            
            // F5 重新连接（仅在断开时）
            if (e.key === 'F5' && !this.isConnected && this.username) {
                e.preventDefault();
                this.reconnect();
            }
        });
    }
    
    updateUsernameCounter() {
        const length = this.usernameInput.value.length;
        this.usernameCounter.textContent = `${length}/20`;
        
        if (length > 18) {
            this.usernameCounter.className = 'char-counter danger';
        } else if (length > 15) {
            this.usernameCounter.className = 'char-counter warning';
        } else {
            this.usernameCounter.className = 'char-counter';
        }
    }
    
    updateCharCounter() {
        const length = this.messageInput.value.length;
        this.charCounter.textContent = `${length}/1000`;
        
        // 更新发送按钮状态
        this.sendBtn.disabled = !this.isConnected || length === 0 || this.isSending;
        
        if (length > 900) {
            this.charCounter.className = 'char-counter danger';
        } else if (length > 800) {
            this.charCounter.className = 'char-counter warning';
        } else {
            this.charCounter.className = 'char-counter';
        }
    }
    
    showNotification(message, type = 'info', duration = 5000) {
        this.notificationMessage.textContent = message;
        this.notification.className = `notification ${type}`;
        this.notification.style.display = 'flex';
        
        // 自动隐藏
        if (duration > 0) {
            setTimeout(() => this.hideNotification(), duration);
        }
    }
    
    hideNotification() {
        this.notification.style.display = 'none';
    }
    
    showUsernameModal() {
        this.usernameModal.style.display = 'flex';
        this.usernameInput.focus();
        this.updateUsernameCounter();
    }
    
    hideUsernameModal() {
        this.usernameModal.style.display = 'none';
    }
    
    showUsernameError(message) {
        this.usernameError.textContent = message;
        this.usernameError.style.display = 'block';
        this.usernameInput.focus();
    }
    
    hideUsernameError() {
        this.usernameError.style.display = 'none';
    }
    
    updateConnectionStatus(status) {
        const indicator = this.connectionIndicator;
        const statusText = this.connectionStatus;
        
        // 移除所有状态类
        indicator.classList.remove('connected', 'disconnected', 'connecting');
        
        switch (status) {
            case 'connected':
                indicator.classList.add('connected');
                statusText.textContent = '已连接';
                break;
            case 'connecting':
                indicator.classList.add('connecting');
                statusText.textContent = '连接中...';
                break;
            case 'disconnected':
            default:
                indicator.classList.add('disconnected');
                statusText.textContent = '已断开';
                break;
        }
    }
    
    joinChat() {
        if (this.isJoining) return;
        
        const username = this.usernameInput.value.trim();
        
        // 验证用户名
        if (!username) {
            this.showUsernameError('请输入用户名');
            return;
        }
        
        if (username.length > 20) {
            this.showUsernameError('用户名不能超过20个字符');
            return;
        }
        
        if (username.length < 2) {
            this.showUsernameError('用户名至少需要2个字符');
            return;
        }
        
        // 检查用户名是否包含非法字符
        if (!/^[\u4e00-\u9fa5a-zA-Z0-9_-]+$/.test(username)) {
            this.showUsernameError('用户名只能包含中文、英文、数字、下划线和连字符');
            return;
        }
        
        this.hideUsernameError();
        this.username = username;
        this.isJoining = true;
        this.joinBtn.disabled = true;
        this.joinBtn.textContent = '加入中...';
        
        this.connectToServer();
    }
    
    connectToServer() {
        this.updateConnectionStatus('connecting');
        
        // 连接Socket.IO服务器
        this.socket = io({
            timeout: 10000,
            reconnection: true,
            reconnectionAttempts: 5,
            reconnectionDelay: 1000
        });
        
        // 连接成功
        this.socket.on('connect', () => {
            console.log('连接到服务器');
            this.isConnected = true;
            this.updateConnectionStatus('connected');
            this.socket.emit('join_room', { username: this.username });
        });
        
        // 连接断开
        this.socket.on('disconnect', (reason) => {
            console.log('与服务器断开连接:', reason);
            this.isConnected = false;
            this.updateConnectionStatus('disconnected');
            this.sendBtn.disabled = true;
            
            if (reason === 'io server disconnect') {
                // 服务器主动断开，不自动重连
                this.showNotification('服务器已断开连接', 'error', 0);
            } else {
                // 网络问题等，会自动重连
                this.showNotification('连接断开，正在尝试重连...', 'warning', 3000);
                this.addSystemMessage('连接断开，正在尝试重连...');
            }
        });
        
        // 重连尝试
        this.socket.on('reconnect', (attemptNumber) => {
            console.log('重连成功，尝试次数:', attemptNumber);
            this.showNotification('重连成功！', 'success', 3000);
            this.addSystemMessage('重新连接成功！');
        });
        
        // 重连失败
        this.socket.on('reconnect_failed', () => {
            console.log('重连失败');
            this.showNotification('无法连接到服务器，请刷新页面重试', 'error', 0);
        });
        
        // 加入成功 - 修复事件名
        this.socket.on('join_room_success', (data) => {
            this.isJoining = false;
            this.hideUsernameModal();
            this.showNotification(`欢迎 ${data.user.username} 加入聊天室！`, 'success', 3000);
            this.messageInput.focus();
            this.updateCharCounter();
            
            // 显示聊天历史
            if (data.chat_history && data.chat_history.length > 0) {
                data.chat_history.forEach(msg => {
                    this.addMessage({
                        username: msg.username,
                        content: msg.content,
                        timestamp: msg.timestamp,
                        message_type: msg.is_ai ? 'ai' : (msg.is_system ? 'system' : 'user'),
                        id: msg.message_id
                    });
                });
            } else {
                this.noMessages.style.display = 'block';
            }
            
            // 更新用户列表
            if (data.online_users) {
                this.updateUsersList(data.online_users);
                this.onlineCount.textContent = data.online_users.length;
            }
        });
        
        // 加入失败 - 修复事件名
        this.socket.on('join_room_error', (data) => {
            this.isJoining = false;
            this.joinBtn.disabled = false;
            this.joinBtn.textContent = '加入聊天';
            this.showUsernameError(data.error);
            this.updateConnectionStatus('disconnected');
        });
        
        // 接收消息
        this.socket.on('message', (data) => {
            this.hideNoMessages();
            this.hideAiThinking(); // 隐藏AI思考指示器
            this.addMessage(data);
        });
        
        // AI开始思考
        this.socket.on('ai_thinking', (data) => {
            this.showAiThinking();
        });
        
        // AI思考完成
        this.socket.on('ai_response', (data) => {
            this.hideAiThinking();
            this.hideNoMessages();
            this.addMessage(data);
        });
        
        // 用户列表更新
        this.socket.on('users_update', (data) => {
            this.updateUsersList(data.users);
            this.onlineCount.textContent = data.count;
        });
        
        // 系统通知
        this.socket.on('system_message', (data) => {
            this.addSystemMessage(data.message);
        });
        
        // 错误处理
        this.socket.on('error', (data) => {
            console.error('Socket错误:', data);
            this.showNotification('发生错误: ' + data.message, 'error');
            this.addSystemMessage('发生错误: ' + data.message);
        });
        
        // 监听打字指示器事件
        this.socket.on('user_typing', (data) => {
            this.showTypingIndicator(data.username);
        });
        
        this.socket.on('user_stopped_typing', (data) => {
            this.hideTypingIndicator();
        });
        
        // 连接超时
        this.socket.on('connect_timeout', () => {
            this.isJoining = false;
            this.joinBtn.disabled = false;
            this.joinBtn.textContent = '加入聊天';
            this.showUsernameError('连接超时，请检查网络连接');
            this.updateConnectionStatus('disconnected');
        });
    }
    
    sendMessage() {
        if (!this.isConnected || this.isSending) {
            this.showNotification('未连接到服务器或正在发送中', 'warning');
            return;
        }
        
        const message = this.messageInput.value.trim();
        if (!message) return;
        
        if (message.length > 1000) {
            this.showNotification('消息不能超过1000个字符', 'warning');
            return;
        }
        
        // 显示发送状态
        this.isSending = true;
        this.sendBtn.disabled = true;
        this.btnText.style.display = 'none';
        this.btnLoading.style.display = 'flex';
        
        // 检查是否是@AI消息
        const isAiMessage = message.includes('@AI');
        
        // 发送消息到服务器
        this.socket.emit('send_message', { message: message });
        
        // 清空输入框
        this.messageInput.value = '';
        this.updateCharCounter();
        
        // 隐藏无消息提示
        this.hideNoMessages();
        
        // 如果是AI消息，延迟显示AI思考指示器
        if (isAiMessage) {
            setTimeout(() => {
                this.showAiThinking();
            }, 800); // 给用户消息一些时间显示
        }
        
        // 重置发送状态（延迟一点时间显示发送中状态）
        setTimeout(() => {
            this.isSending = false;
            this.btnText.style.display = 'inline';
            this.btnLoading.style.display = 'none';
            this.updateCharCounter(); // 重新计算按钮状态
        }, 500);
    }
    
    hideNoMessages() {
        if (this.noMessages) {
            this.noMessages.style.display = 'none';
        }
    }
    
    addMessage(data) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${data.message_type}`;
        messageDiv.setAttribute('data-message-id', data.id || Date.now());
        
        const headerDiv = document.createElement('div');
        headerDiv.className = 'message-header';
        
        const usernameSpan = document.createElement('span');
        usernameSpan.className = `message-username ${data.message_type}`;
        usernameSpan.textContent = data.username;
        
        const timeSpan = document.createElement('span');
        timeSpan.className = 'message-time';
        timeSpan.textContent = new Date(data.timestamp).toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        
        headerDiv.appendChild(usernameSpan);
        headerDiv.appendChild(timeSpan);
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // 处理@AI提及的高亮显示
        if (data.content.includes('@AI')) {
            contentDiv.innerHTML = data.content.replace(/@AI/g, '<span style="color: #28a745; font-weight: bold;">@AI</span>');
        } else {
            contentDiv.textContent = data.content;
        }
        
        messageDiv.appendChild(headerDiv);
        messageDiv.appendChild(contentDiv);
        
        // 添加双击复制功能
        contentDiv.addEventListener('dblclick', () => {
            this.copyMessageContent(data.content);
        });
        
        // 添加消息动画
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateY(10px)';
        
        this.messagesContainer.appendChild(messageDiv);
        
        // 触发动画
        requestAnimationFrame(() => {
            messageDiv.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            messageDiv.style.opacity = '1';
            messageDiv.style.transform = 'translateY(0)';
        });
        
        this.scrollToBottom();
    }
    
    addSystemMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system';
        messageDiv.setAttribute('data-message-id', 'system-' + Date.now());
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = message;
        
        messageDiv.appendChild(contentDiv);
        
        // 添加动画
        messageDiv.style.opacity = '0';
        this.messagesContainer.appendChild(messageDiv);
        
        requestAnimationFrame(() => {
            messageDiv.style.transition = 'opacity 0.3s ease';
            messageDiv.style.opacity = '1';
        });
        
        this.scrollToBottom();
    }
    
    updateUsersList(users) {
        this.usersContainer.innerHTML = '';
        
        if (users.length === 0) {
            const emptyLi = document.createElement('li');
            emptyLi.textContent = '暂无其他用户';
            emptyLi.style.fontStyle = 'italic';
            emptyLi.style.color = '#6c757d';
            this.usersContainer.appendChild(emptyLi);
            return;
        }
        
        users.forEach(user => {
            const li = document.createElement('li');
            li.setAttribute('data-user-id', user.id || user.username);
            
            if (user.is_ai) {
                li.className = 'ai-user';
                li.innerHTML = `${user.username} <span style="font-size: 11px; opacity: 0.8;">(AI)</span>`;
            } else {
                li.textContent = user.username;
                // 高亮当前用户
                if (user.username === this.username) {
                    li.style.fontWeight = 'bold';
                    li.style.background = '#e3f2fd';
                    li.title = '这是您';
                }
            }
            
            // 添加用户状态指示（如果有的话）
            if (user.status) {
                const statusSpan = document.createElement('span');
                statusSpan.className = 'user-status';
                statusSpan.textContent = user.status;
                li.appendChild(statusSpan);
            }
            
            this.usersContainer.appendChild(li);
        });
    }
    
    scrollToBottom() {
        // 平滑滚动到底部
        this.messagesContainer.scrollTo({
            top: this.messagesContainer.scrollHeight,
            behavior: 'smooth'
        });
    }
    
    showAiThinking() {
        // 先检查是否已经存在AI思考指示器
        if (document.getElementById('ai-thinking-indicator')) {
            return;
        }
        
        const thinkingDiv = document.createElement('div');
        thinkingDiv.id = 'ai-thinking-indicator';
        thinkingDiv.className = 'ai-thinking';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const dotsDiv = document.createElement('div');
        dotsDiv.className = 'thinking-dots';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.className = 'thinking-dot';
            dotsDiv.appendChild(dot);
        }
        
        contentDiv.appendChild(dotsDiv);
        thinkingDiv.appendChild(contentDiv);
        
        // 添加动画
        thinkingDiv.style.opacity = '0';
        thinkingDiv.style.transform = 'translateY(10px)';
        
        this.messagesContainer.appendChild(thinkingDiv);
        
        // 触发动画
        requestAnimationFrame(() => {
            thinkingDiv.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            thinkingDiv.style.opacity = '1';
            thinkingDiv.style.transform = 'translateY(0)';
        });
        
        this.scrollToBottom();
    }
    
    hideAiThinking() {
        const thinkingIndicator = document.getElementById('ai-thinking-indicator');
        if (thinkingIndicator) {
            thinkingIndicator.style.transition = 'opacity 0.2s ease';
            thinkingIndicator.style.opacity = '0';
            setTimeout(() => {
                if (thinkingIndicator.parentNode) {
                    thinkingIndicator.parentNode.removeChild(thinkingIndicator);
                }
            }, 200);
        }
    }
    
    handleTyping() {
        if (!this.isConnected) return;
        
        const message = this.messageInput.value.trim();
        
        if (message.length > 0) {
            // 开始打字
            if (!this.isTyping) {
                this.isTyping = true;
                this.socket.emit('typing_start');
            }
            
            // 清除之前的定时器
            if (this.typingTimer) {
                clearTimeout(this.typingTimer);
            }
            
            // 设置停止打字的定时器
            this.typingTimer = setTimeout(() => {
                this.stopTyping();
            }, 1000);
        } else {
            // 输入框为空，停止打字
            this.stopTyping();
        }
    }
    
    stopTyping() {
        if (this.isTyping) {
            this.isTyping = false;
            if (this.socket) {
                this.socket.emit('typing_stop');
            }
        }
        
        if (this.typingTimer) {
            clearTimeout(this.typingTimer);
            this.typingTimer = null;
        }
    }
    
    showTypingIndicator(username) {
        if (username === this.username) return; // 不显示自己的打字指示器
        
        const indicator = this.typingIndicator;
        const span = indicator.querySelector('span');
        
        span.textContent = username;
        indicator.style.display = 'block';
        
        // 滚动到底部以显示指示器
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        this.typingIndicator.style.display = 'none';
    }
    
    reconnect() {
        if (this.isConnected || this.isJoining) {
            return;
        }
        
        this.showNotification('尝试重新连接...', 'info', 3000);
        
        // 关闭现有连接（如果有）
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        
        // 重新连接
        this.connectToServer();
    }
    
    copyMessageContent(content) {
        // 移除HTML标签，只保留纯文本
        const plainText = content.replace(/<[^>]*>/g, '');
        
        if (navigator.clipboard && window.isSecureContext) {
            // 使用现代的 Clipboard API
            navigator.clipboard.writeText(plainText).then(() => {
                this.showNotification('消息已复制到剪贴板', 'success', 2000);
            }).catch(() => {
                this.fallbackCopyTextToClipboard(plainText);
            });
        } else {
            // 降级使用传统方法
            this.fallbackCopyTextToClipboard(plainText);
        }
    }
    
    fallbackCopyTextToClipboard(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
            this.showNotification('消息已复制到剪贴板', 'success', 2000);
        } catch (err) {
            this.showNotification('复制失败，请手动复制', 'error', 3000);
        }
        
        document.body.removeChild(textArea);
    }
    
    // 工具方法：格式化时间
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) {
            return '刚刚';
        } else if (diffMins < 60) {
            return `${diffMins}分钟前`;
        } else if (diffMins < 1440) {
            return `${Math.floor(diffMins / 60)}小时前`;
        } else {
            return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        }
    }
}

// 页面加载完成后初始化聊天客户端
document.addEventListener('DOMContentLoaded', () => {
    const chatClient = new ChatClient();
    
    // 为了调试方便，将实例暴露到全局
    window.chatClient = chatClient;
    
    // 页面可见性变化处理
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden && chatClient.isConnected) {
            // 页面变为可见时，确保滚动到底部
            setTimeout(() => chatClient.scrollToBottom(), 100);
        }
    });
    
    // 窗口大小变化时调整滚动
    window.addEventListener('resize', () => {
        if (chatClient.isConnected) {
            setTimeout(() => chatClient.scrollToBottom(), 100);
        }
    });
});