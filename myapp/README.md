# myapp — Aquilia Full-Feature Showcase

This workspace demonstrates every major Aquilia feature across **7 modules**.

## Quick Start

```bash
cd myapp
aq run dev
# Server starts at http://127.0.0.1:8000
```

## Modules

### 📝 Blogs (`/blogs/`)
**Showcases:** Basic CRUD, Controllers, DI, Pattern Routing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/blogs/` | GET | List all blogs |
| `/blogs/` | POST | Create a blog |
| `/blogs/«id:int»` | GET | Get blog by ID |
| `/blogs/«id:int»` | PUT | Update blog |
| `/blogs/«id:int»` | DELETE | Delete blog |

### 👤 Users (`/users/`)
**Showcases:** Auth, Identity, Password Hashing, Tokens, Sessions, Guards, Faults

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/users/register` | POST | Register new user |
| `/users/login` | POST | Login and get token |
| `/users/profile` | GET | Get current user profile |
| `/users/profile` | PUT | Update profile |
| `/users/` | GET | List all users |
| `/users/«id:int»` | GET | Get user by ID |
| `/users/«id:int»` | DELETE | Delete user |
| `/users/stats` | GET | Module statistics |

### 🛍️ Products (`/products/`)
**Showcases:** AMDL Models, Query Patterns, Effects, Nested Resources, Stock Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/products/` | GET | List (filters: `?category=&min_price=&max_price=`) |
| `/products/` | POST | Create product |
| `/products/search?q=` | GET | Search products |
| `/products/«id»` | GET | Get product |
| `/products/«id»` | PUT | Update product |
| `/products/«id»` | DELETE | Delete product (cascades reviews) |
| `/products/«id»/stock` | PATCH | Adjust stock level |
| `/products/«id»/reviews` | GET | List reviews |
| `/products/«id»/reviews` | POST | Add review (1-5 stars) |

### 💬 Chat (`/chat/`)
**Showcases:** WebSockets, SocketController, Events, Rooms, Presence

**HTTP:** `/chat/rooms` (GET, POST), `/chat/rooms/«id»` (DELETE), `/chat/rooms/«id»/messages` (GET), `/chat/online` (GET), `/chat/stats` (GET)

**WebSocket:** `ws://host/chat` — events: `set_username`, `message`, `join_room`, `leave_room`, `typing`, `list_rooms`

**WebSocket:** `ws://host/notifications` — events: `subscribe`, `unsubscribe`

### ✅ Tasks (`/tasks/`)
**Showcases:** Structured Faults, Recovery Strategies, State Machines, Validation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tasks/` | GET | List (filters: `?status=&priority=&assignee=&tag=`) |
| `/tasks/` | POST | Create task |
| `/tasks/«id»` | GET/PUT/DELETE | CRUD |
| `/tasks/«id»/status` | PATCH | State transition |
| `/tasks/«id»/assign` | PATCH | Assign (quota check) |
| `/tasks/stats` | GET | Statistics |

### 📄 Pages (`/pages/`)
**Showcases:** Templates, HTML Rendering, Lifecycle Hooks, Navigation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/pages/` | GET | Home (HTML) |
| `/pages/about` | GET | About (HTML) |
| `/pages/contact` | GET/POST | Contact form (HTML) |
| `/pages/dashboard` | GET | Dashboard (HTML) |

### 🛒 Sessions (`/sessions/`)
**Showcases:** Session State, Cart, Preferences, Multi-step Wizard

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sessions/info` | GET | Session data |
| `/sessions/cart` | GET/DELETE | View/clear cart |
| `/sessions/cart/add` | POST | Add item |
| `/sessions/cart/coupon` | POST | Apply coupon (SAVE10, SAVE20, HALF) |
| `/sessions/preferences` | GET/PUT/DELETE | Manage preferences |
| `/sessions/wizard` | GET/DELETE | Wizard progress |
| `/sessions/wizard/step/«step:int»` | POST | Submit step |

## Architecture

```
myapp/
├── workspace.py              # All modules + integrations
├── starter.py                # Welcome page (debug mode)
├── config/                   # YAML configuration
└── modules/
    ├── blogs/                # Basic CRUD
    ├── users/                # Auth + DI + Sessions
    ├── products/             # AMDL + Effects + Nested Resources
    │   └── models/product.amdl
    ├── chat/                 # WebSockets + HTTP
    ├── tasks/                # Faults + State Machines
    ├── pages/                # Templates + Lifecycle
    └── sessions/             # Session State + Cart + Wizard
```

## Features Covered

| Feature | Module(s) |
|---------|-----------|
| Controllers & Routing | All |
| DI (Constructor Injection) | users, products, chat, tasks, pages, sessions |
| Sessions (Cart, Prefs, Wizard) | sessions, users |
| Auth (Identity, Tokens, Guards) | users |
| Faults (Domains, Recovery) | tasks, users, products |
| WebSockets (Events, Rooms) | chat |
| Templates (HTML Rendering) | pages |
| AMDL Models | products |
| Lifecycle Hooks | pages, users |
| Pattern Routing | All |
| Nested Resources | products |
| State Machines | tasks |

## Documentation

See `GUIDE.md` in the project root for the complete Aquilia usage guide.