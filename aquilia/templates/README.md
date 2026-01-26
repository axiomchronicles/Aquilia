# AquilaTemplates

First-class Jinja2-based template rendering system for Aquilia, designed for production use with async capabilities, security by default, and seamless DI integration.

## Quick Start

```python
from aquilia import Controller, GET
from aquilia.templates import TemplateEngine

class ProfileController(Controller):
    prefix = "/profile"
    
    def __init__(self, templates: TemplateEngine):
        self.templates = templates
    
    @GET("/")
    async def view(self, ctx):
        return self.render("profile.html", {"user": ctx.identity}, ctx)
```

## Installation

AquilaTemplates is included with Aquilia. Ensure Jinja2 is installed:

```bash
pip install jinja2
```

## Key Features

✅ **Async-capable** - Full async/await support with streaming  
✅ **Secure by default** - Sandboxed execution, autoescape, XSS protection  
✅ **Fast** - Bytecode precompilation and caching  
✅ **DI-integrated** - Inject TemplateEngine in controllers  
✅ **Manifest-driven** - Templates compiled to crous artifacts  
✅ **Hot-reload** - Dev mode updates without restart  
✅ **Observable** - Metrics and tracing built-in  

## CLI Commands

```bash
# Compile templates for production
aq templates compile --mode prod

# Lint templates for errors
aq templates lint

# Inspect template metadata
aq templates inspect users/profile.html

# Clear bytecode cache
aq templates clear-cache --all
```

## Documentation

- [Full Documentation](../../docs/TEMPLATES.md)
- [Blog Example](../examples/templates/blog_example.py)
- [API Reference](../../aquilia/templates/)

## Architecture

```
aquilia/templates/
├── __init__.py          # Public API
├── engine.py            # Template engine core
├── loader.py            # Namespace-aware loader
├── bytecode_cache.py    # Caching system
├── manager.py           # Compilation & linting
├── security.py          # Sandboxing & filters
├── context.py           # Context building
├── middleware.py        # Context injection
└── cli.py               # CLI commands
```

## Security

AquilaTemplates is **secure by default**:

- ✅ Sandboxed Jinja2 environment
- ✅ HTML autoescape enabled
- ✅ Restricted globals/filters/tests
- ✅ XSS protection
- ✅ CSRF token injection
- ✅ Secret redaction

## Performance

- **Bytecode caching**: Templates precompiled to bytecode
- **Template caching**: Compiled objects cached in-memory
- **Streaming**: Large templates streamed to reduce memory
- **Async rendering**: Non-blocking I/O for better concurrency

## Testing

Run the test suite:

```bash
pytest tests/templates/
```

Tests cover:
- Engine core functionality
- Template loading and namespacing
- Security and sandboxing
- Bytecode caching
- Controller integration
- Manager compilation and linting

## Example Usage

### Basic Rendering

```python
from aquilia.templates import TemplateEngine, TemplateLoader

loader = TemplateLoader(["/path/to/templates"])
engine = TemplateEngine(loader, sandbox=True)

html = await engine.render("page.html", {"title": "Hello"})
```

### Controller Integration

```python
class BlogController(Controller):
    def __init__(self, templates: TemplateEngine, repo: BlogRepo):
        self.templates = templates
        self.repo = repo
    
    @GET("/post/«id:int»")
    async def view_post(self, ctx, id: int):
        post = await self.repo.get(id)
        return self.render("blog/post.html", {"post": post}, ctx)
```

### Custom Filters

```python
def format_date(dt, format="%Y-%m-%d"):
    return dt.strftime(format)

engine.register_filter("format_date", format_date)
```

```html
<p>Posted: {{ post.created_at | format_date }}</p>
```

## License

Part of Aquilia framework. See main LICENSE file.
