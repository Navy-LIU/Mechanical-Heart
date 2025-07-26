// AI聊天室客户端JavaScript
class ChatClient {
    constructor() {
        this.socket = null;
        this.username = '';
        this.isConnected = false;
        
        this.initializeElements();
        this.bindEvents();
        this.showUsernameModal();
    }
    
    initializeElements() {
        // DOM元素引用
        this.usernameModal = document.getElementById('username-modal');
        this.usernameInput = document.getElementById('username-input');
        this.joinBtn = document.getElementById('join-btn');
        this.messageInput = document.getElementById('message-input');
        this.sendBtn = document.getElementById('send-btn');
        this.messagesContainer = document.getElementById('messages');
        this.usersContainer = document.getElementById('users');
        this.onlineCount = document.getElementById('online-count');
    }
    
    bindEvents() {
        // 加入聊天室
        this.joinBtn.addEventListener('click', () => this.joinChat());
        this.usernameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.joinChat();
        });
        
        // 发送消息
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
    }
    
    showUsernameModal() {
        this.usernameModal.style.display = 'flex';
        this.usernameInput.focus();
    }
    
    hideUsernameModal() {
        this.usernameModal.style.display = 'none';
    }
    
    joinChat() {
        const username = this.usernameInput.value.trim();
        if (!username) {
            alert('请输入用户名');
            return;
        }
        
        if (username.length > 20) {
            alert('用户名不能超过20个字符');
            return;
        }
        
        this.username = username;
        this.connectToServer();
    }
    
    connectToServer() {
        // 连接Socket.IO服务器
        this.socket = io();
        
        // 连接成功
        this.socket.on('connect', () => {
            console.log('连接到服务器');
            this.isConnected = true;
            this.socket.emit('join_room', { username: this.username });
        });
        
        // 连接断开
        this.socket.on('disconnect', () => {
            console.log('与服务器断开连接');
            this.isConnected = false;
            this.addSystemMessage('与服务器断开连接，正在尝试重连...');
        });
        
        // 加入成功
        this.socket.on('join_success', (data) => {
            this.hideUsernameModal();
            this.addSystemMessage(`欢迎 ${data.username} 加入聊天室！`);
            this.messageInput.focus();
        });
        
        // 加入失败
        this.socket.on('join_error', (data) => {
            alert(data.message);
        });
        
        // 接收消息
        this.socket.on('message', (data) => {
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
            this.addSystemMessage('发生错误: ' + data.message);
        });
    }
    
    sendMessage() {
        if (!this.isConnected) {
            alert('未连接到服务器');
            return;
        }
        
        const message = this.messageInput.value.trim();
        if (!message) return;
        
        if (message.length > 1000) {
            alert('消息不能超过1000个字符');
            return;
        }
        
        // 发送消息到服务器
        this.socket.emit('send_message', { message: message });
        this.messageInput.value = '';
    }
    
    addMessage(data) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${data.message_type}`;
        
        const headerDiv = document.createElement('div');
        headerDiv.className = 'message-header';
        
        const usernameSpan = document.createElement('span');
        usernameSpan.className = `message-username ${data.message_type}`;
        usernameSpan.textContent = data.username;
        
        const timeSpan = document.createElement('span');
        timeSpan.className = 'message-time';
        timeSpan.textContent = new Date(data.timestamp).toLocaleTimeString();
        
        headerDiv.appendChild(usernameSpan);
        headerDiv.appendChild(timeSpan);
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = data.content;
        
        messageDiv.appendChild(headerDiv);
        messageDiv.appendChild(contentDiv);
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    addSystemMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = message;
        
        messageDiv.appendChild(contentDiv);
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    updateUsersList(users) {
        this.usersContainer.innerHTML = '';
        
        users.forEach(user => {
            const li = document.createElement('li');
            li.textContent = user.username;
            if (user.is_ai) {
                li.className = 'ai-user';
                li.textContent += ' (AI)';
            }
            this.usersContainer.appendChild(li);
        });
    }
    
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
}

// 页面加载完成后初始化聊天客户端
document.addEventListener('DOMContentLoaded', () => {
    new ChatClient();
});