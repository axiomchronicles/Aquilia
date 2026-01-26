# AquilaTemplates Integration Guide

Quick guide to integrate AquilaTemplates into your Aquilia application.

## Step 1: Install Dependencies

Ensure Jinja2 is installed:

```bash
pip install jinja2
```

Or if using the full Aquilia package, it's included as a dependency.

## Step 2: Create Templates Directory

Create a `templates/` directory in your module:

```
myapp/
  modules/
    users/
      templates/
        profile.html
        list.html
```

## Step 3: Setup Template Engine (DI)

Register the template engine in your DI container:

```python
# In your app setup
from aquilia.templates import TemplateEngine, TemplateLoader, CrousBytecodeCache

def setup_templates(config):
    """Setup template engine for DI."""
    
    # Discover template directories
    template_dirs = [
        "myapp/modules/users/templates",
        "myapp/modules/auth/templates",
        # Add more as needed
    ]
    
    # Create loader
    loader = TemplateLoader(search_paths=template_dirs)
    
    # Create bytecode cache
    cache = CrousBytecodeCache(cache_dir="artifacts")
    
    # Create engine
    engine = TemplateEngine(
        loader=loader,
        bytecode_cache=cache,
        sandbox=True  # Recommended for production
    )
    
    return engine

# Register in DI
from aquilia.di import Container

container = Container()
container.register_singleton(TemplateEngine, factory=lambda: setup_templates(config))
```

## Step 4: Use in Controllers

Inject `TemplateEngine` in your controller:

```python
from aquilia import Controller, GET
from aquilia.templates import TemplateEngine
from typing import Annotated

class UsersController(Controller):
    prefix = "/users"
    
    def __init__(self, templates: TemplateEngine):
        self.templates = templates
    
    @GET("/")
    async def list(self, ctx):
        users = get_users()  # Your data fetching logic
        return self.render("users/list.html", {"users": users}, ctx)
    
    @GET("/«id:int»")
    async def profile(self, ctx, id: int):
        user = get_user(id)
        return self.render("users/profile.html", {"user": user}, ctx)
```

## Step 5: Compile Templates for Production

Before deploying, compile templates:

```bash
# Compile all templates
aq templates compile --mode prod

# This creates: artifacts/templates.crous
```

Add to your deployment script:

```bash
#!/bin/bash
# deploy.sh

# Compile templates
aq templates compile --mode prod

# Deploy application
# ...
```

## Step 6: (Optional) Setup Middleware

Add template middleware for automatic context injection:

```python
from aquilia.templates import TemplateMiddleware

# In your app setup
middleware = TemplateMiddleware(
    url_for=router.url_for,  # Your URL generation function
    config=app_config,
    csrf_token_func=get_csrf_token  # Your CSRF token function
)

app.add_middleware(middleware)
```

## Directory Structure

Recommended project structure:

```
myapp/
  ├── modules/
  │   ├── users/
  │   │   ├── templates/
  │   │   │   ├── profile.html
  │   │   │   └── list.html
  │   │   ├── controllers.py
  │   │   └── models.py
  │   └── auth/
  │       ├── templates/
  │       │   ├── login.html
  │       │   └── register.html
  │       └── controllers.py
  ├── templates/
  │   ├── layouts/
  │   │   └── base.html
  │   └── components/
  │       └── navbar.html
  ├── artifacts/
  │   └── templates.crous  (generated)
  └── config.py
```

## Common Patterns

### Base Layout

Create a base layout that all templates extend:

**templates/layouts/base.html:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}My App{% endblock %}</title>
    {% block head %}{% endblock %}
</head>
<body>
    {% include "components/navbar.html" %}
    
    <main>
        {% block content %}{% endblock %}
    </main>
    
    <footer>
        <p>&copy; 2026 My App</p>
    </footer>
</body>
</html>
```

### Page Template

**modules/users/templates/profile.html:**
```html
{% extends "layouts/base.html" %}

{% block title %}{{ user.name }}'s Profile{% endblock %}

{% block content %}
    <h1>{{ user.name | e }}</h1>
    <p>{{ user.bio | e }}</p>
{% endblock %}
```

### Component Include

**templates/components/navbar.html:**
```html
<nav>
    <a href="/">Home</a>
    {% if identity %}
        <a href="/profile">{{ identity.username }}</a>
        <a href="/logout">Logout</a>
    {% else %}
        <a href="/login">Login</a>
    {% endif %}
</nav>
```

## Development Workflow

### 1. Create Template

```bash
# Create new template
touch myapp/modules/users/templates/new_page.html
```

### 2. Edit Template

```html
{% extends "layouts/base.html" %}

{% block content %}
    <h1>{{ title }}</h1>
{% endblock %}
```

### 3. Use in Controller

```python
@GET("/new")
async def new_page(self, ctx):
    return self.render("users/new_page.html", {"title": "New Page"}, ctx)
```

### 4. Test in Dev Mode

```bash
# Run with hot-reload
aq run --mode dev
```

Templates reload automatically on changes.

### 5. Lint Before Commit

```bash
# Check for errors
aq templates lint
```

## Production Deployment

### Build Step

```bash
# Compile templates
aq templates compile --mode prod

# Verify compilation
aq templates inspect users/profile.html
```

### Runtime

Templates are loaded from `artifacts/templates.crous` with bytecode cache for fast startup.

## Custom Filters

Register custom filters for domain-specific formatting:

```python
def setup_templates(config):
    loader = TemplateLoader(template_dirs)
    engine = TemplateEngine(loader, sandbox=True)
    
    # Register custom filter
    def format_price(value):
        return f"${value:,.2f}"
    
    engine.register_filter("price", format_price)
    
    return engine
```

**Usage in template:**
```html
<p>Price: {{ product.price | price }}</p>
```

## Troubleshooting

### Template Not Found

**Error:** `TemplateNotFound: users/profile.html`

**Fix:**
1. Check template path: `modules/users/templates/profile.html`
2. Verify template directories in loader setup
3. Run: `aq templates inspect users/profile.html`

### Undefined Variable

**Error:** `UndefinedError: 'user' is undefined`

**Fix:**
1. Pass variable in context: `{"user": user}`
2. Add guard in template: `{% if user is defined %}`
3. Run: `aq templates lint` to find all undefined variables

### Lint Errors

**Error:** Lint finds issues

**Fix:**
```bash
# Run lint with verbose output
aq templates lint --verbose

# Fix issues in templates
# Re-run lint
aq templates lint
```

## Security Best Practices

1. **Always escape user input:**
   ```html
   {{ user.bio | e }}
   ```

2. **Use CSRF tokens in forms:**
   ```html
   <form method="POST">
       <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
   </form>
   ```

3. **Only mark trusted content as safe:**
   ```html
   {{ admin_html | safe }}  <!-- Only for trusted admin content! -->
   ```

4. **Keep sandbox enabled:**
   ```python
   engine = TemplateEngine(loader, sandbox=True)  # Always True in production
   ```

5. **Lint templates regularly:**
   ```bash
   aq templates lint --strict
   ```

## Next Steps

- Read [Full Documentation](TEMPLATES.md)
- See [Blog Example](../examples/templates/blog_example.py)
- Explore [API Reference](../aquilia/templates/)
- Check [Implementation Summary](TEMPLATES_IMPLEMENTATION.md)
