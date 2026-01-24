
from aquilia import Response

async def app(scope, receive, send):
    """Minimal ASGI app with landing page."""
    if scope["type"] != "http":
        return
    
    path = scope["path"]
    method = scope["method"]
    
    # Landing page
    if path == "/" and method == "GET":
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to Aquilia</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #333;
        }
        .container {
            background: white;
            padding: 3rem;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            text-align: center;
        }
        h1 {
            font-size: 3rem;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .subtitle {
            font-size: 1.2rem;
            color: #666;
            margin-bottom: 2rem;
        }
        .status {
            display: inline-block;
            background: #10b981;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: bold;
            margin-bottom: 2rem;
        }
        .quick-start {
            background: #f3f4f6;
            padding: 1.5rem;
            border-radius: 10px;
            margin: 2rem 0;
            text-align: left;
        }
        .quick-start h3 {
            margin-bottom: 1rem;
            color: #374151;
        }
        .code {
            background: #1f2937;
            color: #10b981;
            padding: 1rem;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
            overflow-x: auto;
            margin: 0.5rem 0;
        }
        .links {
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 2rem;
        }
        .link {
            display: inline-block;
            padding: 0.75rem 1.5rem;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .link:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }
        .features {
            margin-top: 2rem;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            text-align: left;
        }
        .feature {
            padding: 1rem;
            background: #f9fafb;
            border-radius: 8px;
        }
        .feature-icon {
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        }
        .feature-title {
            font-weight: bold;
            color: #374151;
            margin-bottom: 0.25rem;
        }
        .feature-desc {
            font-size: 0.85rem;
            color: #6b7280;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Aquilia</h1>
        <div class="subtitle">Modern Python Web Framework</div>
        <div class="status">✓ Server Running</div>
        
        <div class="quick-start">
            <h3>🎯 Quick Start</h3>
            <div class="code">$ aq init workspace my-api</div>
            <div class="code">$ cd my-api</div>
            <div class="code">$ aq add module users --use-controllers</div>
            <div class="code">$ aq generate controller Users</div>
            <div class="code">$ aq run</div>
        </div>
        
        <div class="features">
            <div class="feature">
                <div class="feature-icon">🎯</div>
                <div class="feature-title">Controllers</div>
                <div class="feature-desc">Pattern-based routing</div>
            </div>
            <div class="feature">
                <div class="feature-icon">💉</div>
                <div class="feature-title">DI</div>
                <div class="feature-desc">Dependency injection</div>
            </div>
            <div class="feature">
                <div class="feature-icon">⚡</div>
                <div class="feature-title">Fast</div>
                <div class="feature-desc">ASGI-based</div>
            </div>
            <div class="feature">
                <div class="feature-icon">🛡️</div>
                <div class="feature-title">Safe</div>
                <div class="feature-desc">Type-safe routing</div>
            </div>
        </div>
        
        <div class="links">
            <a href="https://github.com/embrake/Aquilify" class="link">📚 Documentation</a>
            <a href="https://github.com/embrake/Aquilify" class="link">⭐ GitHub</a>
        </div>
    </div>
</body>
</html>
"""
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"text/html; charset=utf-8"]],
        })
        await send({
            "type": "http.response.body",
            "body": html.encode("utf-8"),
        })
        return
    
    # API endpoint
    if path == "/api/health" and method == "GET":
        import json
        body = json.dumps({"status": "healthy", "message": "Aquilia is running!"})
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"application/json"]],
        })
        await send({
            "type": "http.response.body",
            "body": body.encode("utf-8"),
        })
        return
    
    # 404
    await send({
        "type": "http.response.start",
        "status": 404,
        "headers": [[b"content-type", b"text/plain"]],
    })
    await send({
        "type": "http.response.body",
        "body": b"Not Found",
    })
