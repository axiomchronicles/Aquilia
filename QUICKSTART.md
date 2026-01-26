#!/usr/bin/env markdown
# Quick Start Guide - Aquilia Authentication Dashboard

## One-Minute Setup

### 1. Start the server
```bash
cd /Users/kuroyami/PyProjects/Aquilia
python -m aquilia.server myapp
```

Expected output:
```
INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 2. Open your browser
Visit: `http://localhost:8000/auth/login`

### 3. Login with demo credentials
- **Username**: `admin`
- **Password**: `password`

Or try the regular user:
- **Username**: `john`
- **Password**: `password`

### 4. Explore
- Dashboard: `http://localhost:8000/dashboard`
- Profile: `http://localhost:8000/profile`
- Sessions: `http://localhost:8000/sessions/list`
- Logout: `http://localhost:8000/auth/logout`

## What You're Seeing

### Login Flow
1. ✅ **POST /auth/login** - Validates credentials with Argon2id hashing
2. ✅ **Session Creation** - Generates secure session ID and stores in memory
3. ✅ **Cookie Setting** - HttpOnly cookie with SameSite=Lax protection
4. ✅ **Redirect** - Redirects to dashboard (HTTP 302)

### Dashboard
1. ✅ **Session Resolution** - Middleware loads session from cookie
2. ✅ **Identity Extraction** - Loads user from session.principal
3. ✅ **Context Injection** - Passes user/session to template
4. ✅ **Template Rendering** - Jinja2 renders with user info

### Middleware Pipeline
```
Request
  ↓
[AquilAuthMiddleware] → Loads identity from bearer token (if present)
  ↓
[SessionMiddleware] → Resolves session from cookie
  ↓
[TemplateMiddleware] → Prepares template context
  ↓
[Controller] → Executes route handler
  ↓
[Response] → Renders template with injected context
```

## How It Works

### Authentication
```python
# User provides: admin / password
# DemoAuthService.verify_credentials() does:
1. Find user by username
2. Get stored password hash: $argon2id$v=19$m=65536...
3. Use PasswordHasher.verify(hash, password)
4. Constant-time comparison (prevents timing attacks)
5. Return identity if match
```

### Session Management
```python
# After successful login:
1. Create Session object with cryptographic ID (sess_xxx)
2. Set session.principal = identity (admin-001)
3. Store in MemoryStore with TTL=7 days, idle=1 hour
4. Write session ID to HttpOnly cookie
5. Middleware automatically loads session on next request
```

### Template Context
```python
# In templates, you can access:
{{ user.username }}           # Current user's username
{{ user.email }}              # User's email
{{ user.has_role('admin') }}  # Check if user is admin
{{ session.id }}              # Session ID
{{ request.path }}            # Current URL path
{{ _flash_messages }}         # Success/error messages
```

## Key Features Demonstrated

### 1. Password Security ✅
- Algorithm: **Argon2id** (GPU-resistant, memory-hard)
- Memory: **64MB** per hash
- Iterations: **2** (optimized for speed+security)
- Comparison: **Constant-time** (prevents timing attacks)

### 2. Session Security ✅
- Cookie: **HttpOnly** (JavaScript can't access)
- CSRF: **SameSite=Lax** (protects against cross-site requests)
- Expiry: **7 days** TTL + **1 hour** idle timeout
- ID: **32-byte** cryptographic random

### 3. Template Security ✅
- HTML: **Auto-escaped** by Jinja2 (prevents XSS)
- Context: **Injected** by middleware (server-side)
- Files: **Loaded** from templates directory only
- Variables: **Type-safe** checks available

### 4. Dependency Injection ✅
- Services: **App-scoped** (singletons)
- Injection: **Automatic** based on type hints
- Lifecycle: **Managed** by container
- Testing: **Easy** to mock services

### 5. Middleware Chain ✅
- Priority: **Ordered** by importance
- Context: **Available** in every handler
- Async: **Full** async/await support
- Composable: **Reusable** across modules

## Troubleshooting

### Q: Login page doesn't show
**A**: Check that templates directory exists:
```bash
ls myapp/modules/myappmod/templates/
```
Should show: `base.html  dashboard.html  login.html  profile.html  sessions.html`

### Q: "Invalid username or password" error
**A**: Try the demo credentials:
- Username: `admin` (exact case)
- Password: `password`

### Q: Session times out too quickly
**A**: Check session TTL settings in manifest.py or modify:
```python
SessionPolicy(
    ttl=timedelta(days=7),        # Increase this
    idle_timeout=timedelta(hours=1),  # Or this
    ...
)
```

### Q: Can't access database
**A**: Memory store doesn't persist across restarts. All data is in-memory only. For persistence, configure PostgreSQL or Redis in production.

### Q: SSL/TLS certificate error
**A**: For development, this is expected. In production:
1. Get certificate from Let's Encrypt
2. Set `secure=True` on cookies
3. Redirect HTTP to HTTPS

## Advanced Topics

### Create New User (JSON API)
```bash
curl -X POST http://localhost:8000/myappmod/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "SecurePass123!",
    "email": "alice@example.com",
    "roles": ["user"]
  }'
```

### Get Current User (Protected)
```bash
# First, login to get session cookie
curl -X POST http://localhost:8000/myappmod/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}' \
  -c cookies.txt

# Then use cookie to access protected endpoint
curl http://localhost:8000/myappmod/auth/me \
  -b cookies.txt
```

### Bearer Token Authentication
```bash
curl -X POST http://localhost:8000/myappmod/auth/login-json \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Response includes access_token, use it:
curl -H "Authorization: Bearer {access_token}" \
  http://localhost:8000/myappmod/auth/me
```

## File Structure
```
myapp/modules/myappmod/
├── auth.py                    ← Services & Controllers (365 lines)
├── manifest.py                ← Configuration & registration
├── workspace.py               ← Module setup
├── templates/
│   ├── base.html             ← Master layout
│   ├── login.html            ← Login form
│   ├── dashboard.html        ← Main dashboard
│   ├── profile.html          ← User profile
│   └── sessions.html         ← Session info
└── ...other modules

tests/
└── test_auth_integration.py   ← 4 passing tests
```

## Running Tests
```bash
cd /Users/kuroyami/PyProjects/Aquilia
python test_auth_integration.py
```

Expected output:
```
============================================================
Authentication Dashboard Integration Tests
============================================================
✓ Demo users seeded successfully
✓ Credentials storage test passed
✓ DemoAuthService tests passed
✓ AuthController login page test passed
============================================================
✓ All tests passed!
============================================================
```

## Next Steps

### To Learn More
1. Read: `docs/AUTH_DASHBOARD_INTEGRATION.md` - Full architecture
2. Check: `myapp/modules/myappmod/auth.py` - Implementation details
3. Browse: `myapp/modules/myappmod/templates/` - Template examples

### To Extend
1. Add new route: Create method in controller with `@GET` or `@POST`
2. Add new template: Create HTML file in templates/ directory
3. Register services: Add to manifest.py `services=[]` list
4. Update middleware: Register in manifest.py `middleware=[]` list

### To Deploy
1. Switch to PostgreSQL/Redis from memory store
2. Enable HTTPS and secure cookies
3. Add CSRF tokens to forms
4. Implement rate limiting
5. Set up proper logging

## Support

For issues or questions:
1. Check the logs: `server.log`
2. Review test output: `python test_auth_integration.py -v`
3. Inspect controller: `myapp/modules/myappmod/auth.py`
4. Check documentation: `docs/AUTH_DASHBOARD_INTEGRATION.md`

---

**🚀 You're ready to go!**

Start the server and visit `http://localhost:8000/auth/login`

