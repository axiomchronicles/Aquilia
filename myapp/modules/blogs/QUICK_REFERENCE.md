# Quick Reference: DI-Serializer Integration

## ⚡ FastAPI-Style Auto-Injection

```python
from aquilia import Controller, POST, RequestCtx, Response
from .serializers import BlogPostSerializer

class BlogsController(Controller):
    @POST("/blogs/")
    async def create(self, ctx: RequestCtx, serializer: BlogPostSerializer):
        # ✅ serializer is already validated
        # ✅ DI defaults are injected
        # ✅ Faults are raised on validation errors
        item = await self.service.create(serializer.validated_data)
        return Response.json(item, status=201)
```

## 🔐 DI-Aware Defaults

```python
from aquilia import Serializer, CharField, HiddenField
from aquilia import CurrentUserDefault, CurrentRequestDefault, InjectDefault

class MySerializer(Serializer):
    title = CharField(max_length=200)
    
    # Auto-inject user ID
    author_id = HiddenField(default=CurrentUserDefault())
    
    # Auto-inject request attribute
    client_ip = HiddenField(default=CurrentRequestDefault(attr="client_ip"))
    
    # Auto-inject service from DI
    rate = HiddenField(default=InjectDefault("RateService", method="get_rate"))
```

## ✅ Enhanced Validators

```python
from aquilia import IntegerField, CharField
from aquilia import RangeValidator, CompoundValidator, ConditionalValidator
from aquilia.serializers.validators import MinLengthValidator

# Range (min + max in one)
age = IntegerField(validators=[RangeValidator(0, 150)])

# Compound (AND/OR logic)
password = CharField(validators=[
    CompoundValidator(
        MinLengthValidator(8),
        # ... more validators
        mode="and",
    )
])

# Conditional (context-aware)
email = CharField(validators=[
    ConditionalValidator(
        condition=lambda data: data.get("notify") is True,
        validator=MinLengthValidator(5),
    )
])
```

## 🎨 Response Serialization

```python
from aquilia import GET, RequestCtx
from .serializers import BlogPostSerializer

@GET("/blogs/", response_serializer=BlogPostSerializer)
async def list_blogs(self, ctx: RequestCtx):
    items = await self.service.get_all()
    return items  # Auto-serialized by decorator
```

## 🧪 Testing with DI Context

```python
from aquilia import Serializer, CharField, HiddenField, CurrentUserDefault

class FakeIdentity:
    def __init__(self, id=42):
        self.id = id

# Create serializer with DI context
serializer = MySerializer(
    data={"title": "Test"},
    context={
        "identity": FakeIdentity(id=99),
    }
)

assert serializer.is_valid()
assert serializer.validated_data["author_id"] == 99  # Auto-injected!
```

## 📖 More Info

- **Demo**: Run `python3.14 myapp/modules/blogs/demo.py`
- **Examples**: See `myapp/modules/blogs/serializers.py`
- **Advanced**: See `myapp/modules/blogs/examples_advanced.py`
- **Docs**: See `myapp/modules/blogs/README.md`
- **Summary**: See `myapp/modules/blogs/INTEGRATION_SUMMARY.md`

## 🎯 Parameter Naming Convention

```python
# Full serializer instance (can call .save(), .errors, etc.)
async def create_a(self, ctx, serializer: BlogSerializer):
    pass

async def create_b(self, ctx, blog_ser: BlogSerializer):
    pass

# Just validated_data dict
async def create_c(self, ctx, blog_data: BlogSerializer):
    pass
```

**Rule**: If param name is `serializer` or ends with `_serializer` / `_ser`, you get the full instance. Otherwise, you get just `validated_data`.

---

**Built for Aquilia Framework - Phase 8 Complete ✅**
