# AquilaTemplates

**First-class Jinja2-based template rendering for Aquilia**

Production-ready, async-capable template system with manifest-driven compilation, DI integration, and security by default.

## Features

- ✅ **Async-capable**: Full async rendering with streaming support
- ✅ **Manifest-driven**: Templates discovered and compiled per module
- ✅ **DI-friendly**: Seamless dependency injection in Controllers
- ✅ **Secure by default**: Sandboxed execution, autoescape, limited globals
- ✅ **Fast**: Bytecode precompilation, caching, and streaming
- ✅ **Hot-reload friendly**: Dev mode updates without restart
- ✅ **Observable**: Metrics and tracing built-in
- ✅ **Extensible**: Custom filters, tests, globals, and i18n support

## Quick Start

### 1. Create Templates

Create a `templates/` directory in your module:

```
myapp/
  modules/
    users/
      templates/
        profile.html
        list.html
```

**templates/profile.html:**
```html
{% extends "layouts/base.html" %}

{% block title %}Profile - {{ user.name }}{% endblock %}

{% block content %}
  <h1>{{ user.name | e }}</h1>
  <p>Email: {{ user.email | e }}</p>
  
  {% if session and session.model.roles %}
    <p>Roles: {{ session.model.roles | join(", ") }}</p>
  {% endif %}
  
  <a href="{{ url_for('users_list') }}">Back to Users</a>
{% endblock %}
```

### 2. Controller Integration

Inject `TemplateEngine` in your controller:

```python
from aquilia import Controller, GET, Inject
from aquilia.templates import TemplateEngine
from typing import Annotated

class UsersController(Controller):
    prefix = "/users"
    
    def __init__(
        self,
        templates: TemplateEngine,
        repo: Annotated[UserRepo, Inject(tag="repo")]
    ):
        self.templates = templates
        self.repo = repo
    
    @GET("/profile/«id:int»")
    async def profile(self, ctx, id: int):
        user = await self.repo.get(id)
        
        # Render template with automatic context injection
        return self.render("users/profile.html", {"user": user}, ctx)
    
    @GET("/")
    async def list(self, ctx):
        users = await self.repo.list_all()
        return self.render("users/list.html", {"users": users}, ctx)
```

### 3. Compile Templates

Precompile templates for production:

```bash
# Compile all templates
aq templates compile --mode prod --out artifacts/templates.crous

# Lint templates
aq templates lint

# Inspect specific template
aq templates inspect users/profile.html

# Clear cache
aq templates clear-cache --all
```

## Installation

AquilaTemplates is included with Aquilia. Ensure Jinja2 is installed:

```bash
pip install jinja2
```

For Redis bytecode cache (optional):

```bash
pip install redis
```

## Template Structure

### Directory Layout

Templates follow module namespace conventions:

```
templates/
  layouts/
    base.html
    admin.html
  components/
    navbar.html
    footer.html

modules/
  users/
    templates/
      profile.html
      list.html
      edit.html
  auth/
    templates/
      login.html
      register.html
```

### Template Naming

- **Relative**: `profile.html` → resolved in current module
- **Module-namespaced**: `users/profile.html` → `modules/users/templates/profile.html`
- **Cross-module (@)**: `@auth/login.html` → `modules/auth/templates/login.html`
- **Fully-qualified (:)**: `users:profile.html` → `modules/users/templates/profile.html`

## Template Syntax

AquilaTemplates uses standard Jinja2 syntax with security enhancements.

### Variables

```html
{{ user.name }}           <!-- Output variable -->
{{ text | escape }}       <!-- Apply filter -->
{{ items | length }}      <!-- Built-in filter -->
```

### Control Flow

```html
{% if user.is_admin %}
  <p>Admin panel</p>
{% elif user.is_moderator %}
  <p>Moderator tools</p>
{% else %}
  <p>User dashboard</p>
{% endif %}

{% for item in items %}
  <li>{{ item.name }}</li>
{% endfor %}
```

### Template Inheritance

**layouts/base.html:**
```html
<!DOCTYPE html>
<html>
<head>
  <title>{% block title %}My App{% endblock %}</title>
</head>
<body>
  {% block content %}{% endblock %}
</body>
</html>
```

**users/profile.html:**
```html
{% extends "layouts/base.html" %}

{% block title %}{{ user.name }} - Profile{% endblock %}

{% block content %}
  <h1>{{ user.name }}</h1>
{% endblock %}
```

### Includes

```html
{% include "components/navbar.html" %}

<main>
  {% block content %}{% endblock %}
</main>

{% include "components/footer.html" %}
```

## Framework Integration

### Automatic Context Injection

Controllers automatically inject framework variables:

- `request` - HTTP request object
- `session` - Active session (if available)
- `identity` - Authenticated user (if auth successful)
- `url_for(name, **params)` - URL generation
- `static_url(path)` - Static asset URLs
- `csrf_token` - CSRF token (if sessions enabled)
- `config` - Safe config subset

**Example:**
```html
<form method="POST" action="{{ url_for('users_update', id=user.id) }}">
  <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
  
  {% if identity %}
    <p>Logged in as {{ identity.username }}</p>
  {% endif %}
  
  <button>Save</button>
</form>
```

### Response Helpers

**Direct rendering:**
```python
from aquilia.response import Response

@GET("/page")
async def page(self, ctx):
    return Response.render(
        "page.html",
        {"title": "Page"},
        engine=self.templates,
        request_ctx=ctx
    )
```

**Controller helper (recommended):**
```python
@GET("/page")
async def page(self, ctx):
    return self.render("page.html", {"title": "Page"}, ctx)
```

**Streaming response:**
```python
@GET("/large")
async def large_page(self, ctx):
    return self.templates.template_stream_response(
        "large.html",
        {"data": large_dataset},
        request_ctx=ctx
    )
```

## Custom Filters

Register custom filters for domain-specific formatting:

```python
from aquilia.templates import TemplateEngine

# In DI setup
def setup_templates(engine: TemplateEngine):
    # Date formatting
    def format_datetime(dt, format="%Y-%m-%d %H:%M"):
        return dt.strftime(format)
    
    engine.register_filter("datetime", format_datetime)
    
    # Markdown rendering
    def markdown(text):
        import markdown
        return markdown.markdown(text)
    
    engine.register_filter("markdown", markdown)
    
    # Custom business logic
    def format_price(value, currency="USD"):
        return f"${value:.2f}"
    
    engine.register_filter("price", format_price)
```

**Usage in templates:**
```html
<p>Posted: {{ post.created_at | datetime("%B %d, %Y") }}</p>
<div>{{ post.content | markdown | safe }}</div>
<span>Price: {{ product.price | price }}</span>
```

## Security

AquilaTemplates is **secure by default** with multiple layers of protection.

### Sandboxed Execution

Templates run in a sandboxed Jinja2 environment with restricted operations:

```python
from aquilia.templates import SandboxPolicy

# Strict policy (production default)
policy = SandboxPolicy.strict()

# Permissive policy (development)
policy = SandboxPolicy.permissive()
```

### Autoescape

HTML autoescaping is **enabled by default** for `.html`, `.htm`, and `.xml` files:

```html
{{ user_input }}              <!-- Automatically escaped -->
{{ user_input | e }}          <!-- Explicit escape -->
{{ trusted_html | safe }}     <!-- Mark as safe (use cautiously) -->
```

### Allowed Operations

**Strict policy allows:**
- Safe filters: `upper`, `lower`, `escape`, `length`, `join`, etc.
- Safe tests: `defined`, `undefined`, `even`, `odd`, etc.
- Safe globals: `url_for`, `static_url`, `csrf_token`, `config`

**Strict policy blocks:**
- File system access
- Code execution (`eval`, `exec`, `__import__`)
- Unsafe filters (`tojson` without explicit allowlist)
- Arbitrary object access

### Registering Safe Filters

Add filters to the allowlist:

```python
from aquilia.templates import TemplateSandbox, SandboxPolicy

sandbox = TemplateSandbox(policy=SandboxPolicy.strict())
sandbox.register_filter("custom_safe_filter", my_filter_func)
```

### XSS Prevention

1. **Autoescape** - Enabled by default for HTML
2. **Content Security Policy** - Set via middleware
3. **CSRF tokens** - Automatic injection in forms
4. **Sanitize user input** - Use `sanitize_html` filter

```html
<!-- Safe: auto-escaped -->
<p>{{ user.bio }}</p>

<!-- Sanitized HTML (removes scripts, keeps formatting) -->
<div>{{ user.bio | sanitize_html }}</div>

<!-- Trusted admin content -->
<div>{{ admin_html | safe }}</div>
```

## Performance

### Bytecode Caching

Templates are precompiled to bytecode:

```bash
# Precompile for production
aq templates compile --mode prod
```

**Cache backends:**
- `InMemoryBytecodeCache` - Fast, non-persistent (dev)
- `CrousBytecodeCache` - Persistent, fingerprinted (prod)
- `RedisBytecodeCache` - Distributed cache (high-throughput)

### Template Caching

Compiled template objects are cached in memory with LRU eviction:

```python
# Configure cache
engine = TemplateEngine(
    loader=loader,
    bytecode_cache=CrousBytecodeCache(capacity=1000)
)

# Invalidate specific template
engine.invalidate_cache("users/profile.html")

# Clear all caches
engine.invalidate_cache()
```

### Streaming

For large templates, use streaming to reduce memory:

```python
@GET("/report")
async def report(self, ctx):
    return self.templates.template_stream_response(
        "reports/annual.html",
        {"data": large_dataset},
        request_ctx=ctx
    )
```

## CLI Commands

### Compile

Precompile all templates to crous artifacts:

```bash
aq templates compile [OPTIONS]

Options:
  --dirs PATH         Template directories (auto-discovered if omitted)
  --out PATH          Output file (default: artifacts/templates.crous)
  --mode dev|prod     Compilation mode
  --verbose           Verbose output
```

**Example:**
```bash
aq templates compile --mode prod --verbose
```

### Lint

Check templates for errors and issues:

```bash
aq templates lint [OPTIONS]

Options:
  --dirs PATH         Template directories
  --strict            Treat warnings as errors
  --json              Output JSON for LSP integration
  --verbose           Verbose output
```

**Example:**
```bash
aq templates lint --strict
```

### Inspect

View template metadata:

```bash
aq templates inspect NAME [OPTIONS]

Options:
  --dirs PATH         Template directories
  --verbose           Verbose output
```

**Example:**
```bash
aq templates inspect users/profile.html
```

### Clear Cache

Clear compiled bytecode cache:

```bash
aq templates clear-cache [OPTIONS]

Options:
  --template NAME     Specific template to clear
  --cache-dir PATH    Cache directory (default: artifacts)
  --all               Clear all caches
  --verbose           Verbose output
```

**Example:**
```bash
aq templates clear-cache --all
```

## Development

### Hot Reload

In dev mode, templates automatically reload on changes:

```bash
aq run --mode dev
```

Template-only changes don't require process restart.

### Debugging

**View compilation issues:**
```bash
aq templates lint --verbose
```

**Inspect template metadata:**
```bash
aq templates inspect users/profile.html
```

**Test rendering:**
```python
# In Python shell
from aquilia.templates import TemplateEngine, TemplateLoader

loader = TemplateLoader(["templates"])
engine = TemplateEngine(loader)

result = await engine.render("test.html", {"name": "Debug"})
print(result)
```

## Observability

### Metrics

AquilaTemplates emits Prometheus metrics:

- `templates_render_total{template}` - Total renders
- `templates_render_latency_seconds{template}` - Render latency histogram
- `templates_cache_hit_total` - Cache hits
- `templates_cache_miss_total` - Cache misses

### Tracing

Each render emits an OpenTelemetry span:

```
templates.render
  attributes:
    template.name: "users/profile.html"
    app.module: "users"
    render.duration_ms: 3.2
```

## Best Practices

### 1. Use Template Inheritance

Define base layouts and extend them:

```html
<!-- layouts/base.html -->
<!DOCTYPE html>
<html>
<head>
  <title>{% block title %}{% endblock %}</title>
  {% block head %}{% endblock %}
</head>
<body>
  {% include "components/navbar.html" %}
  
  <main>
    {% block content %}{% endblock %}
  </main>
  
  {% include "components/footer.html" %}
</body>
</html>
```

### 2. Escape User Input

Always escape unless you explicitly trust the content:

```html
<!-- Safe -->
<p>{{ user.comment }}</p>

<!-- Safe with explicit escape -->
<p>{{ user.comment | e }}</p>

<!-- Dangerous - only for trusted admin content -->
<div>{{ admin_html | safe }}</div>
```

### 3. Modular Components

Break templates into reusable components:

```html
<!-- components/user_card.html -->
<div class="user-card">
  <h3>{{ user.name }}</h3>
  <p>{{ user.bio }}</p>
</div>

<!-- users/list.html -->
{% for user in users %}
  {% include "components/user_card.html" %}
{% endfor %}
```

### 4. Precompile for Production

Always precompile templates before deployment:

```bash
aq templates compile --mode prod
```

### 5. Use Streaming for Large Pages

Reduce memory usage with streaming:

```python
return self.templates.template_stream_response("large.html", ctx)
```

## Migration from Function-Based Views

**Before (function-based):**
```python
@flow("/profile")
async def profile(ctx):
    user = get_user(ctx.identity.id)
    html = f"<h1>{user.name}</h1>"
    return Response.html(html)
```

**After (template-based):**
```python
class UsersController(Controller):
    def __init__(self, templates: TemplateEngine):
        self.templates = templates
    
    @GET("/profile")
    async def profile(self, ctx):
        user = get_user(ctx.identity.id)
        return self.render("users/profile.html", {"user": user}, ctx)
```

## Troubleshooting

### Template Not Found

**Error:** `TemplateNotFound: users/profile.html`

**Solutions:**
1. Check template directory structure
2. Verify module namespace
3. Run `aq templates inspect users/profile.html`

### Undefined Variable

**Error:** `UndefinedError: 'user' is undefined`

**Solutions:**
1. Pass variable in context: `{"user": user}`
2. Check variable name spelling
3. Use `{% if user is defined %}` guard

### Lint Errors

Run lint to diagnose:
```bash
aq templates lint --verbose
```

## API Reference

See individual module documentation:

- `aquilia.templates.engine` - Template engine core
- `aquilia.templates.loader` - Template loading
- `aquilia.templates.manager` - Compilation and linting
- `aquilia.templates.security` - Sandboxing and filters
- `aquilia.templates.context` - Context building

## License

AquilaTemplates is part of Aquilia and follows the same license.
