/**
 * Aquilia Chat - WebSocket Client
 * 
 * Handles real-time communication with the Aquilia chat server.
 */

class AquiliaChat {
    constructor() {
        this.ws = null;
        this.currentRoom = 'general';
        this.username = 'guest';
        this.isTyping = false;
        this.typingTimeout = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        this.initializeElements();
        this.attachEventListeners();
        this.connect();
        this.loadRooms();
    }
    
    initializeElements() {
        // Main elements
        this.messagesContainer = document.getElementById('messages-container');
        this.messageInput = document.getElementById('message-input');
        this.sendBtn = document.getElementById('send-btn');
        this.roomList = document.getElementById('room-list');
        this.userList = document.getElementById('user-list');
        this.currentUsername = document.getElementById('current-username');
        this.roomTitle = document.getElementById('room-title');
        this.roomDescription = document.getElementById('room-description');
        this.typingIndicator = document.getElementById('typing-indicator');
        this.connectionStatus = document.getElementById('connection-status');
        this.onlineCount = document.getElementById('online-count');
        
        // Modals
        this.usernameModal = document.getElementById('username-modal');
        this.createRoomModal = document.getElementById('create-room-modal');
        this.usernameInput = document.getElementById('username-input');
        this.roomNameInput = document.getElementById('room-name-input');
        this.roomDescInput = document.getElementById('room-desc-input');
        this.roomPublicInput = document.getElementById('room-public-input');
        
        // Stats
        this.statRooms = document.getElementById('stat-rooms');
        this.statMessages = document.getElementById('stat-messages');
    }
    
    attachEventListeners() {
        // Send message
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
        
        // Typing indicator
        this.messageInput.addEventListener('input', () => this.handleTyping());
        
        // Username modal
        document.getElementById('edit-username-btn').addEventListener('click', () => {
            this.usernameInput.value = this.username;
            this.showModal(this.usernameModal);
        });
        document.getElementById('save-username-btn').addEventListener('click', () => this.saveUsername());
        document.getElementById('cancel-username-btn').addEventListener('click', () => this.hideModal(this.usernameModal));
        
        // Create room modal
        document.getElementById('create-room-btn').addEventListener('click', () => {
            this.showModal(this.createRoomModal);
        });
        document.getElementById('create-room-submit-btn').addEventListener('click', () => this.createRoom());
        document.getElementById('cancel-room-btn').addEventListener('click', () => this.hideModal(this.createRoomModal));
        
        // Room actions
        document.getElementById('leave-room-btn').addEventListener('click', () => this.leaveCurrentRoom());
        
        // Room selection
        this.roomList.addEventListener('click', (e) => {
            const roomItem = e.target.closest('.room-item');
            if (roomItem) {
                const room = roomItem.dataset.room;
                this.switchRoom(room);
            }
        });
    }
    
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/chat`;
        
        this.updateConnectionStatus('connecting', 'Connecting...');
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => this.onConnect();
        this.ws.onmessage = (event) => this.onMessage(event);
        this.ws.onclose = () => this.onDisconnect();
        this.ws.onerror = (error) => this.onError(error);
    }
    
    onConnect() {
        console.log('Connected to Aquilia Chat');
        this.updateConnectionStatus('connected', 'Connected');
        this.reconnectAttempts = 0;
    }
    
    onMessage(event) {
        // Handle Blob (binary frame) by reading as text first
        if (event.data instanceof Blob) {
            event.data.text().then(text => this._processMessage(text));
            return;
        }
        this._processMessage(event.data);
    }

    _processMessage(raw) {
        try {
            const data = JSON.parse(raw);
            console.log('Received:', data);

            // Unwrap Aquilia MessageEnvelope if present:
            // envelope format: { type:"event", event:"...", payload:{...}, meta:{...} }
            // raw format:      { type:"system"|"message"|..., event:"...", data:{...} }
            let msg = data;
            if (data.type === 'event' && data.payload !== undefined) {
                // Envelope-wrapped message from publish_room / adapter
                msg = data.payload;
                // Preserve the event name if the payload doesn't have one
                if (!msg.event && data.event) msg.event = data.event;
            }

            switch (msg.type) {
                case 'system':
                    this.handleSystemMessage(msg);
                    break;
                case 'message':
                    this.handleChatMessage(msg);
                    break;
                case 'presence':
                    this.handlePresence(msg);
                    break;
                case 'error':
                    this.handleError(msg);
                    break;
                default:
                    // AckEvent responses (e.g. {status:'ok', ...})
                    // These are picked up by sendWithAck listeners
                    break;
            }
        } catch (error) {
            console.error('Failed to parse message:', error);
        }
    }
    
    onDisconnect() {
        console.log('Disconnected from Aquilia Chat');
        this.updateConnectionStatus('disconnected', 'Disconnected');
        
        // Attempt to reconnect
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => this.connect(), 2000 * this.reconnectAttempts);
        }
    }
    
    onError(error) {
        console.error('WebSocket error:', error);
        this.updateConnectionStatus('disconnected', 'Connection Error');
    }
    
    handleSystemMessage(data) {
        const { event, data: payload } = data;
        
        switch (event) {
            case 'welcome':
                this.username = payload.username;
                this.currentUsername.textContent = this.username;
                this.currentRoom = payload.default_room;
                break;
                
            case 'user_joined':
                this.addSystemMessage(`${payload.username} joined ${payload.room}`);
                this.updateOnlineUsers();
                break;
                
            case 'user_left':
                this.addSystemMessage(`${payload.username} left ${payload.room}`);
                this.updateOnlineUsers();
                break;
                
            case 'username_changed':
                this.addSystemMessage(`${payload.old_username} is now ${payload.new_username}`);
                break;
        }
    }
    
    handleChatMessage(data) {
        const { data: payload } = data;
        
        if (payload.room === this.currentRoom) {
            this.addChatMessage(payload.from, payload.text, payload.connection_id);
            this.hideTypingIndicator();
        } else {
            // Show unread badge
            this.showUnreadBadge(payload.room);
        }
    }
    
    handlePresence(data) {
        const { data: payload } = data;
        
        if (payload.event === 'typing') {
            if (payload.room === this.currentRoom) {
                if (payload.is_typing) {
                    this.showTypingIndicator(payload.username);
                } else {
                    this.hideTypingIndicator();
                }
            }
        }
    }
    
    handleError(data) {
        const { data: payload } = data;
        this.showNotification(payload.message, 'error');
    }
    
    sendMessage() {
        const text = this.messageInput.value.trim();
        if (!text) return;
        
        this.send('message', {
            text: text,
            room: this.currentRoom
        });
        
        this.messageInput.value = '';
        this.stopTyping();
    }
    
    handleTyping() {
        if (!this.isTyping) {
            this.isTyping = true;
            this.send('typing', { room: this.currentRoom }, true); // Subscribe
        }
        
        clearTimeout(this.typingTimeout);
        this.typingTimeout = setTimeout(() => this.stopTyping(), 3000);
    }
    
    stopTyping() {
        if (this.isTyping) {
            this.isTyping = false;
            this.send('typing', { room: this.currentRoom }, false); // Unsubscribe
        }
    }
    
    saveUsername() {
        const newUsername = this.usernameInput.value.trim();
        if (!newUsername) return;
        
        this.sendWithAck('set_username', { username: newUsername })
            .then(response => {
                if (response.status === 'ok') {
                    this.username = response.username;
                    this.currentUsername.textContent = this.username;
                    this.hideModal(this.usernameModal);
                    this.showNotification('Username updated!', 'success');
                } else {
                    this.showNotification(response.message, 'error');
                }
            });
    }
    
    createRoom() {
        const name = this.roomNameInput.value.trim();
        const description = this.roomDescInput.value.trim();
        const isPublic = this.roomPublicInput.checked;
        
        if (!name) {
            this.showNotification('Room name is required', 'error');
            return;
        }
        
        fetch('/chat/rooms', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description, is_public: isPublic })
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                this.showNotification(data.error, 'error');
            } else {
                this.hideModal(this.createRoomModal);
                this.loadRooms();
                this.showNotification('Room created!', 'success');
                this.switchRoom(data.id);
            }
        })
        .catch(err => {
            this.showNotification('Failed to create room', 'error');
        });
    }
    
    switchRoom(roomId) {
        if (roomId === this.currentRoom) return;
        
        // Leave current room (except general)
        if (this.currentRoom !== 'general') {
            this.sendWithAck('leave_room', { room: this.currentRoom });
        }
        
        // Join new room
        this.sendWithAck('join_room', { room: roomId })
            .then(response => {
                if (response.status === 'ok') {
                    this.currentRoom = roomId;
                    this.roomTitle.textContent = roomId;
                    this.updateRoomUI(roomId);
                    this.loadMessageHistory(roomId);
                } else {
                    this.showNotification(response.message, 'error');
                }
            });
    }
    
    leaveCurrentRoom() {
        if (this.currentRoom === 'general') {
            this.showNotification('Cannot leave the general room', 'error');
            return;
        }
        
        this.sendWithAck('leave_room', { room: this.currentRoom })
            .then(response => {
                if (response.status === 'ok') {
                    this.currentRoom = 'general';
                    this.roomTitle.textContent = 'General';
                    this.updateRoomUI('general');
                    this.loadMessageHistory('general');
                }
            });
    }
    
    updateRoomUI(roomId) {
        // Update active room in sidebar
        document.querySelectorAll('.room-item').forEach(item => {
            item.classList.toggle('active', item.dataset.room === roomId);
        });
        
        // Clear unread badge
        const roomItem = document.querySelector(`.room-item[data-room="${roomId}"]`);
        if (roomItem) {
            const badge = roomItem.querySelector('.unread-badge');
            if (badge) badge.style.display = 'none';
        }
        
        // Clear messages
        this.messagesContainer.innerHTML = '';
    }
    
    loadRooms() {
        fetch('/chat/rooms')
            .then(res => res.json())
            .then(data => {
                this.statRooms.textContent = data.total;
                // Update room list if needed
            });
    }
    
    loadMessageHistory(roomId) {
        fetch(`/chat/rooms/${roomId}/messages?limit=50`)
            .then(res => res.json())
            .then(data => {
                data.messages.forEach(msg => {
                    this.addChatMessage(msg.sender, msg.text, msg.connection_id, false);
                });
                this.scrollToBottom();
            });
    }
    
    updateOnlineUsers() {
        fetch('/chat/online')
            .then(res => res.json())
            .then(data => {
                this.onlineCount.textContent = data.count;
                
                this.userList.innerHTML = '';
                data.online_users.forEach(username => {
                    const li = document.createElement('li');
                    li.className = 'user-item';
                    li.innerHTML = `
                        <span class="status-dot online"></span>
                        <span class="user-name">${this.escapeHtml(username)}</span>
                    `;
                    this.userList.appendChild(li);
                });
            });
    }
    
    addChatMessage(sender, text, connId, scroll = true) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message';
        
        const avatar = sender.charAt(0).toUpperCase();
        const time = new Date().toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-sender">${this.escapeHtml(sender)}</span>
                    <span class="message-time">${time}</span>
                </div>
                <div class="message-text">${this.escapeHtml(text)}</div>
            </div>
        `;
        
        this.messagesContainer.appendChild(messageDiv);
        
        if (scroll) this.scrollToBottom();
        
        // Update stats
        this.updateStats();
    }
    
    addSystemMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'system-message';
        messageDiv.textContent = text;
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    showTypingIndicator(username) {
        this.typingIndicator.querySelector('.typing-user').textContent = `${username} is typing`;
        this.typingIndicator.style.display = 'flex';
    }
    
    hideTypingIndicator() {
        this.typingIndicator.style.display = 'none';
    }
    
    showUnreadBadge(roomId) {
        const roomItem = document.querySelector(`.room-item[data-room="${roomId}"]`);
        if (roomItem) {
            const badge = roomItem.querySelector('.unread-badge');
            if (badge) {
                badge.style.display = 'inline';
                const count = parseInt(badge.textContent) || 0;
                badge.textContent = count + 1;
            }
        }
    }
    
    updateStats() {
        fetch('/chat/stats')
            .then(res => res.json())
            .then(data => {
                this.statMessages.textContent = data.total_messages || 0;
            });
    }
    
    updateConnectionStatus(status, text) {
        this.connectionStatus.className = `connection-status ${status}`;
        this.connectionStatus.querySelector('.status-text').textContent = text;
    }
    
    showModal(modal) {
        modal.style.display = 'flex';
    }
    
    hideModal(modal) {
        modal.style.display = 'none';
    }
    
    showNotification(message, type = 'info') {
        // Simple alert for now - can be enhanced with toast notifications
        console.log(`[${type.toUpperCase()}] ${message}`);
        
        // Add visual feedback
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: ${type === 'error' ? '#ED4245' : type === 'success' ? '#3BA55D' : '#5865F2'};
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 1001;
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
    
    send(event, data, subscribe = null) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const message = {
                event: event,
                data: data
            };
            
            if (subscribe !== null) {
                message.subscribe = subscribe;
            }
            
            this.ws.send(JSON.stringify(message));
        }
    }
    
    sendWithAck(event, data) {
        return new Promise((resolve, reject) => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                const handler = (msgEvent) => {
                    const raw = (msgEvent.data instanceof Blob)
                        ? null : msgEvent.data;
                    if (!raw) return;
                    try {
                        let response = JSON.parse(raw);
                        // Unwrap envelope if present
                        if (response.type === 'event' && response.payload !== undefined) {
                            response = response.payload;
                        }
                        // AckEvent responses have a 'status' field
                        if (response.status !== undefined) {
                            this.ws.removeEventListener('message', handler);
                            resolve(response);
                        }
                    } catch (e) {
                        // Not our message
                    }
                };
                
                this.ws.addEventListener('message', handler);
                
                this.ws.send(JSON.stringify({
                    event: event,
                    data: data
                }));
                
                // Timeout after 5 seconds
                setTimeout(() => {
                    this.ws.removeEventListener('message', handler);
                    reject(new Error('Request timeout'));
                }, 5000);
            } else {
                reject(new Error('WebSocket not connected'));
            }
        });
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize chat when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.chat = new AquiliaChat();
    
    // Load initial data
    window.chat.updateOnlineUsers();
    window.chat.updateStats();
    
    // Periodic updates
    setInterval(() => {
        window.chat.updateOnlineUsers();
        window.chat.updateStats();
    }, 10000);
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
