# Aquilia Chat - Complete Real-time Chat Application

A production-ready, feature-rich chat application built with Aquilia's template engine, WebSockets, and service architecture.

## Features

✨ **Real-time Messaging**
- WebSocket-based instant messaging
- Multiple chat rooms
- Typing indicators
- Online presence tracking
- Message history

🎨 **Modern UI**
- Discord-inspired dark theme
- Responsive design
- Smooth animations
- Modal dialogs
- Toast notifications

🏗️ **Architecture**
- Template-driven UI with Jinja2
- WebSocket controllers for real-time events
- Service layer for business logic
- In-memory message persistence
- DI-based component injection

## Quick Start

### 1. Start the Application

```bash
# From the myapp directory
python starter.py
```

### 2. Access the Chat

Open your browser and navigate to:
```
http://localhost:8000/chat
```

### 3. Start Chatting

1. **Set Your Username**: Click the edit icon (✏️) next to your username
2. **Join Rooms**: Click on any room in the sidebar or create a new one
3. **Send Messages**: Type in the input box and press Enter or click Send
4. **Switch Rooms**: Click on different rooms in the sidebar

## Project Structure

```
myapp/modules/chat/
├── controllers.py          # HTTP endpoints + template rendering
├── sockets.py             # WebSocket event handlers
├── services.py            # Business logic (rooms, messages, presence)
├── manifest.py            # Module configuration
├── templates/
│   ├── base.html          # Base template layout
│   └── chat/
│       ├── index.html     # Main chat interface
│       └── room.html      # Room details page
└── static/
    ├── css/
    │   └── chat.css       # Complete chat styling
    └── js/
        └── chat.js        # WebSocket client + UI logic
```

## Architecture Deep Dive

### Controllers (HTTP Layer)

**ChatController** handles:
- `GET /chat` - Render main chat UI
- `GET /chat/room/<id>` - Render room details
- `GET /chat/rooms` - List all rooms (JSON API)
- `POST /chat/rooms` - Create new room
- `DELETE /chat/rooms/<id>` - Delete room
- `GET /chat/rooms/<id>/messages` - Get message history
- `GET /chat/online` - Get online users
- `GET /chat/stats` - Get chat statistics

### WebSocket Layer

**ChatSocket** (`/chat` namespace) handles:
- `@OnConnect` - User joins, gets assigned username
- `@OnDisconnect` - Cleanup and notifications
- `set_username` - Change username (with acknowledgment)
- `message` - Send chat message
- `join_room` - Join a room (with acknowledgment)
- `leave_room` - Leave a room (with acknowledgment)
- `typing` (Subscribe/Unsubscribe) - Typing indicators
- `list_rooms` - Get available rooms (with acknowledgment)

### Service Layer

**ChatRoomService** (App-scoped):
- Manages room metadata
- CRUD operations for rooms
- Pre-seeded with "General" and "Random" rooms

**MessageService** (App-scoped):
- Stores last 100 messages per room
- Provides message history
- Message statistics
- Seeded with welcome messages

**PresenceService** (App-scoped):
- Tracks online users
- Room membership tracking
- User connection/disconnection handling
- Online user count and lists

## Template System

### Base Template (`base.html`)

Provides:
- HTML5 structure
- CSS/JS loading
- Responsive viewport
- Content blocks

### Chat Interface (`chat/index.html`)

Components:
- **Sidebar**
  - User info with username editor
  - Room list with active states
  - Online users list
  - Statistics display
- **Main Chat Area**
  - Room header with actions
  - Scrollable message container
  - Typing indicators
  - Message input with emoji button
- **Modals**
  - Username editor
  - Room creation dialog
- **Connection Status**
  - Real-time connection indicator

### Room Details (`chat/room.html`)

Displays:
- Room information
- Recent message preview
- Join/Delete actions

## WebSocket Client (`chat.js`)

### Class: AquiliaChat

**Initialization**:
```javascript
const chat = new AquiliaChat();
```

**Key Methods**:
- `connect()` - Establish WebSocket connection
- `sendMessage()` - Send chat message
- `switchRoom(roomId)` - Change active room
- `saveUsername()` - Update username
- `createRoom()` - Create new room
- `addChatMessage()` - Render message in UI
- `updateOnlineUsers()` - Refresh online users list
- `handleTyping()` - Manage typing indicators

**Event Handlers**:
- `onConnect()` - Connection established
- `onMessage()` - Incoming WebSocket message
- `onDisconnect()` - Connection lost
- `handleSystemMessage()` - System events (join/leave/username change)
- `handleChatMessage()` - New chat message
- `handlePresence()` - Presence updates (typing, online status)

## Styling (`chat.css`)

### CSS Variables

```css
--primary-color: #5865F2      /* Primary actions */
--bg-primary: #36393F         /* Main backgrounds */
--bg-secondary: #2F3136       /* Sidebar */
--bg-tertiary: #202225        /* Darker elements */
--online-color: #3BA55D       /* Online status */
--danger-color: #ED4245       /* Destructive actions */
```

### Key Components

- **Layout**: Flexbox-based sidebar + main area
- **Messages**: Hover effects, timestamps, avatars
- **Modals**: Centered overlays with backdrop
- **Animations**: Smooth transitions, typing dots, pulse effects
- **Scrollbars**: Custom styled for dark theme
- **Responsive**: Mobile-friendly breakpoints

## API Endpoints

### REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/chat` | Main chat UI (HTML) |
| GET | `/chat/room/<id>` | Room details (HTML) |
| GET | `/chat/rooms` | List rooms (JSON) |
| POST | `/chat/rooms` | Create room (JSON) |
| DELETE | `/chat/rooms/<id>` | Delete room (JSON) |
| GET | `/chat/rooms/<id>/messages` | Message history (JSON) |
| GET | `/chat/online` | Online users (JSON) |
| GET | `/chat/stats` | Statistics (JSON) |

### WebSocket Events

**Client → Server**:
```javascript
// Send message
ws.send(JSON.stringify({
    event: "message",
    data: { text: "Hello!", room: "general" }
}));

// Set username (with acknowledgment)
ws.send(JSON.stringify({
    event: "set_username",
    data: { username: "Alice" },
    ack: true,
    ack_id: 12345
}));
```

**Server → Client**:
```javascript
// System message
{
    type: "system",
    event: "user_joined",
    data: { username: "Alice", room: "general" }
}

// Chat message
{
    type: "message",
    event: "new_message",
    data: { text: "Hi!", from: "Alice", room: "general" }
}

// Typing indicator
{
    type: "presence",
    event: "typing",
    data: { username: "Bob", room: "general", is_typing: true }
}
```

## Customization

### Adding New Rooms

Modify `services.py`:
```python
self._rooms: Dict[str, Dict[str, Any]] = {
    "general": {...},
    "random": {...},
    "your-room": {
        "id": "your-room",
        "name": "Your Room",
        "description": "Custom room description",
        "created_at": datetime.utcnow().isoformat(),
        "is_public": True,
    }
}
```

### Changing Theme Colors

Edit `chat.css`:
```css
:root {
    --primary-color: #YOUR_COLOR;
    --bg-primary: #YOUR_BG;
    /* ... */
}
```

### Adding Message Types

Extend `MessageService`:
```python
message_type: str = "text"  # text, image, file, system
```

Update UI in `chat.js`:
```javascript
addChatMessage(sender, text, connId, type='text') {
    // Handle different message types
}
```

## Production Considerations

### Performance
- ✅ Message history limited to 100 per room
- ✅ Bytecode-cached templates
- ✅ Efficient WebSocket broadcasting
- ⚠️ Consider Redis for distributed presence
- ⚠️ Use database for persistent message storage

### Security
- ✅ HTML escaping in templates
- ✅ Input validation (message length, username)
- ✅ XSS protection via escapeHtml()
- ⚠️ Add authentication/authorization
- ⚠️ Rate limiting for message sending
- ⚠️ Profanity filtering

### Scalability
- ✅ Service layer abstraction
- ✅ DI for easy testing/mocking
- ⚠️ Implement Redis pub/sub for multi-server
- ⚠️ Use PostgreSQL for message persistence
- ⚠️ Add horizontal scaling with load balancer

## Development

### Running Tests

```bash
pytest tests/chat/
```

### Hot Reload

Templates and static files reload automatically in development mode.

### Debugging WebSockets

Browser DevTools → Network → WS → Messages

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests
4. Submit pull request

## License

MIT

## Credits

Built with:
- [Aquilia](https://github.com/aquilia/aquilia) - Async Python web framework
- [Jinja2](https://jinja.palletsprojects.com/) - Template engine
- WebSocket API - Real-time communication

---

**Aquilia Chat** - Modern real-time messaging, powered by Python 🚀
