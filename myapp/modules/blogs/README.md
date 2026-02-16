# Blogs Module - DI-Serializer Integration Demo

This module demonstrates the **deep DI-Serializer integration** features added to Aquilia, bringing FastAPI-style ergonomics with Django DRF-like serializers.

## 🎯 Key Features Demonstrated

### 1. FastAPI-Style Serializer Auto-Injection

Controllers can receive validated serializers by simply type-hinting parameters:

```python
@POST("/blogs/")
async def create_blog(
    self, 
    ctx: RequestCtx,
    serializer: BlogPostSerializer,  # ← Auto-injected & validated!
):
    # serializer.validated_data is ready to use
    item = await self.service.create(serializer.validated_data)
    return Response.json(item, status=201)
```

**What happens automatically:**
1. Request body is parsed (JSON or form)
2. Serializer is instantiated with the data
3. `.is_valid(raise_fault=True)` is called
4. DI container and request are wired into serializer context
5. All DI-aware defaults are resolved

### 2. DI-Aware Field Defaults

Serializer fields can automatically inject values from the request context and DI container:

```python
class BlogPostSerializer(Serializer):
    title = CharField(max_length=200)
    content = CharField()
    
    # Auto-inject authenticated user's ID
    author_id = HiddenField(
        default=CurrentUserDefault()
    )
    
    # Auto-inject client IP for audit logging
    client_ip = HiddenField(
        default=CurrentRequestDefault(attr="client_ip")
    )
    
    # Auto-inject any service from DI container
    moderation_score = HiddenField(
        default=InjectDefault("ModerationService", method="calculate")
    )
```

**Available DI Defaults:**
- `CurrentUserDefault()` - Resolves `identity.id` from request/container
- `CurrentRequestDefault(attr="...")` - Injects request or its attributes
- `InjectDefault(token, method=None, tag=None)` - Resolves any service from DI

### 3. Response Serialization

Automatically serialize handler return values:

```python
@GET("/", response_serializer=BlogPostListSerializer)
async def list_blogs(self, ctx: RequestCtx):
    items = await self.service.get_all()
    # Return raw objects - serializer handles conversion
    return items
```

### 4. Enhanced Validators

**RangeValidator** - Combined min/max:
```python
age = IntegerField(validators=[RangeValidator(0, 150)])
```

**CompoundValidator** - AND/OR logic:
```python
password = CharField(validators=[
    CompoundValidator(
        MinLengthValidator(8),
        RegexValidator(r"[A-Z]"),  # Must have uppercase
        RegexValidator(r"[0-9]"),  # Must have digit
        mode="and",
    )
])
```

**ConditionalValidator** - Context-aware validation:
```python
email = EmailField(
    required=False,
    validators=[
        ConditionalValidator(
            condition=lambda data: data.get("notify_reply") is True,
            validator=MinLengthValidator(5),
        )
    ]
)
```

## 📁 Files in This Module

- **`serializers.py`** - Complete serializer definitions with DI integration
- **`controllers.py`** - Controller handlers demonstrating all features
- **`examples_advanced.py`** - Advanced patterns and best practices
- **`services.py`** - Business logic layer
- **`faults.py`** - Custom exception definitions

## 🚀 Quick Start

### 1. Basic POST Handler with Auto-Validation

```python
@POST("/blogs/")
async def create_blog(self, ctx: RequestCtx, serializer: BlogPostSerializer):
    # serializer is already validated!
    # serializer.validated_data includes DI-injected defaults
    item = await self.service.create(serializer.validated_data)
    return Response.json(item, status=201)
```

**Request:**
```json
POST /blogs/
{
    "title": "My First Post",
    "content": "This is the content...",
    "published": true
}
```

**What happens:**
- `author_id` is auto-populated from `CurrentUserDefault` (e.g., 42)
- `client_ip` is auto-populated from `CurrentRequestDefault` (e.g., "192.168.1.1")
- All validations run automatically
- If validation fails, `ValidationFault` is raised with error details

### 2. Inject Validated Data Only

```python
@POST("/blogs/alt")
async def create_blog_alt(
    self, 
    ctx: RequestCtx,
    post_data: BlogPostSerializer,  # ← No _serializer suffix
):
    # post_data is the validated dict (not the serializer instance)
    item = await self.service.create(post_data)
    return Response.json(item, status=201)
```

**Naming convention:**
- Parameter name = `serializer` or ends with `_serializer` / `_ser` → Full serializer instance
- Otherwise → `validated_data` dict only

### 3. Response Serialization

```python
@GET("/«id:int»", response_serializer=BlogPostSerializer)
async def get_blog(self, ctx: RequestCtx, id: int):
    item = await self.service.get_by_id(id)
    # Return raw object - response_serializer converts it
    return item
```

For lists:
```python
@GET("/", response_serializer=BlogPostSerializer)
async def list_blogs(self, ctx: RequestCtx):
    items = await self.service.get_all()
    return items  # Automatically wrapped with ListSerializer
```

### 4. Partial Updates

```python
@PATCH("/«id:int»")
async def partial_update(
    self, 
    ctx: RequestCtx, 
    id: int,
    update_data: BlogPostUpdateSerializer,
):
    # All fields are optional in the update serializer
    # updated_by is auto-populated via CurrentUserDefault
    item = await self.service.update(id, update_data)
    return Response.json(item)
```

## 🧪 Testing Serializers with DI

```python
from aquilia.serializers import Serializer

# Mock dependencies
class FakeIdentity:
    def __init__(self, id=42):
        self.id = id

class FakeRequest:
    def __init__(self, identity=None):
        self.client_ip = "127.0.0.1"
        self.state = {"identity": identity}

# Test with DI context
identity = FakeIdentity(id=42)
request = FakeRequest(identity=identity)

serializer = BlogPostSerializer(
    data={
        "title": "Test Post",
        "content": "Test content...",
    },
    context={
        "request": request,
        "identity": identity,
    }
)

assert serializer.is_valid()
assert serializer.validated_data["author_id"] == 42  # Auto-injected!
```

## 📚 Advanced Patterns

See `examples_advanced.py` for:

1. **Custom DI-aware defaults** - Create your own injectable defaults
2. **Nested serializers with DI** - DI works in nested contexts
3. **Serializer inheritance** - Base classes with audit fields
4. **ModelSerializer with DI** - Auto-field generation + DI defaults
5. **Custom validation with services** - Access DI container in validate methods
6. **SerializerProvider** - Register serializers in DI for constructor injection
7. **Testing patterns** - Complete test examples

## 🔗 Integration with Aquilia Systems

The DI-serializer integration works seamlessly with:

- **DI Container** - Serializers resolve services via `InjectDefault`
- **Auth System** - `CurrentUserDefault` works with any auth middleware
- **Session System** - Access session data via `CurrentRequestDefault(attr="session")`
- **Fault System** - Validation errors become `ValidationFault` with structured errors
- **Controller System** - Auto-detection in `_bind_parameters`, response serialization
- **OpenAPI** - Serializers can generate OpenAPI schemas (future enhancement)

## 🎨 Design Philosophy

This integration brings together the best of:

- **Django DRF** - Declarative serializers with field-based validation
- **FastAPI** - Type-hint driven auto-injection with DI container
- **Aquilia** - Pattern-based routing, fault domain, lifecycle hooks

The result is a **production-ready serialization system** that:
- ✅ Eliminates boilerplate
- ✅ Enforces validation at the framework level
- ✅ Integrates deeply with DI for testability
- ✅ Provides clear error messages
- ✅ Maintains type safety

## 🚦 Running the Examples

1. Start the Aquilia server:
```bash
cd /Users/kuroyami/PyProjects/Aquilia/myapp
python3.14 starter.py
```

2. Test the endpoints:
```bash
# Create a blog post (author_id auto-injected)
curl -X POST http://localhost:8000/blogs/ \
  -H "Content-Type: application/json" \
  -d '{"title": "My Post", "content": "Content here...", "published": true}'

# Get blog post (auto-serialized response)
curl http://localhost:8000/blogs/1

# Partial update (updated_by auto-injected)
curl -X PATCH http://localhost:8000/blogs/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title"}'

# Create comment with conditional validation
curl -X POST http://localhost:8000/blogs/1/comments \
  -H "Content-Type: application/json" \
  -d '{
    "post_id": 1,
    "author_name": "Kai",
    "content": "Great post!",
    "notify_reply": true,
    "email": "kai@example.com"
  }'
```

## 📊 Test Coverage

**243 serializer tests** covering:
- All field types
- DI-aware defaults (CurrentUserDefault, CurrentRequestDefault, InjectDefault)
- Enhanced validators (RangeValidator, CompoundValidator, ConditionalValidator)
- Serializer factories (from_request, from_request_async)
- Controller engine integration
- SerializerProvider
- Response serialization

**1887 total tests** across entire Aquilia framework (all passing).

---

**Built with ❤️ for the Aquilia framework**
