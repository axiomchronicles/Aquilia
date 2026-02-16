"""
Advanced DI-Serializer Integration Examples

This file demonstrates advanced patterns and best practices for
using the new DI-serializer integration in Aquilia.

Topics covered:
1. Custom DI-aware defaults
2. Nested serializers with DI
3. Serializer inheritance with DI defaults
4. ModelSerializer with DI integration
5. Custom validation with DI services
6. SerializerProvider in DI container
7. Testing serializers with DI
"""

from datetime import datetime
from aquilia import (
    Serializer,
    ModelSerializer,
    CharField,
    IntegerField,
    DateTimeField,
    EmailField,
    BooleanField,
    HiddenField,
    CurrentUserDefault,
    CurrentRequestDefault,
    InjectDefault,
    RangeValidator,
    CompoundValidator,
    ConditionalValidator,
)
from aquilia.serializers.validators import (
    MinLengthValidator,
    MaxLengthValidator,
)
from aquilia.di import Container, service
from aquilia.serializers.fields import _DIAwareDefault


# ============================================================================
# 1. Custom DI-Aware Defaults
# ============================================================================

class CurrentTimestampDefault(_DIAwareDefault):
    """
    Custom DI-aware default that injects current timestamp.
    
    Can optionally resolve a TimeService from the DI container
    to handle timezone-aware timestamps or custom time sources.
    """
    
    def __init__(self, use_service: bool = False):
        self.use_service = use_service
    
    def resolve(self, context: dict) -> datetime:
        """Resolve current timestamp, optionally from service."""
        if self.use_service:
            container = context.get("container")
            if container:
                try:
                    time_service = container.resolve("TimeService", optional=True)
                    if time_service and hasattr(time_service, "now"):
                        return time_service.now()
                except Exception:
                    pass
        return datetime.utcnow()


class TenantIdDefault(_DIAwareDefault):
    """
    Custom DI-aware default for multi-tenant applications.
    
    Resolves tenant_id from:
    1. Request headers (X-Tenant-ID)
    2. Request subdomain
    3. Authenticated user's tenant
    4. DI container
    """
    
    def resolve(self, context: dict) -> int | None:
        """Resolve tenant ID from various sources."""
        request = context.get("request")
        
        # Try request header
        if request:
            headers = getattr(request, "headers", {})
            tenant_id = headers.get("x-tenant-id")
            if tenant_id:
                return int(tenant_id)
            
            # Try subdomain
            host = headers.get("host", "")
            if "." in host:
                subdomain = host.split(".")[0]
                # In real app, lookup tenant by subdomain
                # return await TenantService.get_by_subdomain(subdomain)
        
        # Try authenticated user's tenant
        identity = context.get("identity")
        if identity and hasattr(identity, "tenant_id"):
            return identity.tenant_id
        
        # Try DI container
        container = context.get("container")
        if container:
            try:
                return container.resolve("tenant_id", optional=True)
            except Exception:
                pass
        
        return None


# ============================================================================
# 2. Nested Serializers with DI
# ============================================================================

class AuthorSerializer(Serializer):
    """Nested serializer for author information."""
    
    id = IntegerField(read_only=True)
    username = CharField(max_length=150)
    email = EmailField(read_only=True)
    is_active = BooleanField(read_only=True)


class ArticleSerializer(Serializer):
    """
    Article serializer with nested author and DI-aware defaults.
    
    The author field is read-only and auto-populated from CurrentUserDefault.
    """
    
    id = IntegerField(read_only=True)
    title = CharField(max_length=200)
    content = CharField()
    
    # Nested serializer for output
    author = AuthorSerializer(read_only=True)
    
    # DI-aware: Auto-populate author_id from authenticated user
    author_id = HiddenField(
        default=CurrentUserDefault(),
    )
    
    # Custom DI default for timestamps
    created_at = DateTimeField(
        read_only=True,
        default=CurrentTimestampDefault(use_service=True)
    )
    
    # Multi-tenant support
    tenant_id = HiddenField(
        default=TenantIdDefault(),
    )


# ============================================================================
# 3. Serializer Inheritance with DI Defaults
# ============================================================================

class AuditedSerializer(Serializer):
    """
    Base serializer with audit fields.
    
    All subclasses automatically get audit tracking via DI defaults.
    """
    
    created_by = HiddenField(
        default=CurrentUserDefault(),
        required=False,  # Optional for system-created records
    )
    
    created_ip = HiddenField(
        default=CurrentRequestDefault(attr="client_ip"),
        required=False,
    )
    
    created_at = DateTimeField(
        read_only=True,
        default=CurrentTimestampDefault(),
    )


class ProductSerializer(AuditedSerializer):
    """
    Product serializer inherits audit fields from AuditedSerializer.
    
    All products automatically track who created them and when.
    """
    
    id = IntegerField(read_only=True)
    name = CharField(max_length=200)
    price = IntegerField(validators=[RangeValidator(0, 1_000_000)])
    sku = CharField(max_length=50)
    
    # Inherits: created_by, created_ip, created_at (all with DI defaults)


# ============================================================================
# 4. ModelSerializer with DI Integration (if using Aquilia ORM)
# ============================================================================

# Assuming you have a Blog model:
# from myapp.modules.blogs.models import Blog

# class BlogModelSerializer(ModelSerializer):
#     """
#     ModelSerializer with DI-aware defaults.
#     
#     Auto-generates fields from the Blog model and adds DI defaults.
#     """
#     
#     # Override auto-generated field to add DI default
#     author_id = HiddenField(default=CurrentUserDefault())
#     client_ip = HiddenField(default=CurrentRequestDefault(attr="client_ip"))
#     
#     class Meta:
#         model = Blog
#         fields = ["id", "title", "content", "author_id", "client_ip", "created_at"]
#         read_only_fields = ["id", "created_at"]


# ============================================================================
# 5. Custom Validation with DI Services
# ============================================================================

@service(scope="app")
class ModerationService:
    """
    Example moderation service for content validation.
    """
    
    def check_content(self, text: str) -> bool:
        """Check if content passes moderation."""
        # In real app: ML model, external API, etc.
        banned_words = ["spam", "scam", "phishing"]
        return not any(word in text.lower() for word in banned_words)
    
    def calculate_trust_score(self, user_id: int) -> float:
        """Calculate user trust score."""
        # In real app: historical behavior analysis
        return 0.85


class ModeratedContentSerializer(Serializer):
    """
    Serializer with custom validation using injected service.
    
    The validation method can access DI services via self.container.
    """
    
    title = CharField(max_length=200)
    content = CharField()
    author_id = HiddenField(default=CurrentUserDefault())
    
    def validate_content(self, value: str) -> str:
        """Validate content using ModerationService from DI container."""
        # Access DI container from serializer context
        if self.container:
            try:
                moderator = self.container.resolve(ModerationService)
                if not moderator.check_content(value):
                    raise ValueError("Content failed moderation check")
            except Exception:
                # Service not available, skip moderation
                pass
        
        return value
    
    def validate(self, attrs: dict) -> dict:
        """Cross-field validation with DI services."""
        if self.container:
            try:
                moderator = self.container.resolve(ModerationService)
                author_id = attrs.get("author_id")
                
                if author_id:
                    trust_score = moderator.calculate_trust_score(author_id)
                    
                    # Low-trust users have stricter content requirements
                    if trust_score < 0.5:
                        if len(attrs.get("content", "")) < 50:
                            raise ValueError(
                                "Low-trust users must provide more detailed content"
                            )
            except Exception:
                pass
        
        return attrs


# ============================================================================
# 6. SerializerProvider in DI Container
# ============================================================================

def setup_serializer_providers(container: Container):
    """
    Register serializers in the DI container for automatic injection.
    
    This allows controllers to receive serializers via constructor injection
    instead of parameter injection.
    """
    from aquilia.di.providers import SerializerProvider
    
    # Register serializers as DI providers
    container.register(
        SerializerProvider(
            ArticleSerializer,
            scope="request",
            auto_validate=True,  # Automatically call is_valid()
        )
    )
    
    container.register(
        SerializerProvider(
            ProductSerializer,
            scope="request",
            auto_validate=False,  # Manual validation
        )
    )


# ============================================================================
# 7. Testing Serializers with DI
# ============================================================================

class _FakeIdentity:
    """Test stub for identity."""
    def __init__(self, id=1, username="test_user"):
        self.id = id
        self.username = username


class _FakeRequest:
    """Test stub for request."""
    def __init__(self, identity=None, client_ip="127.0.0.1"):
        self.client_ip = client_ip
        self.state = {}
        if identity:
            self.state["identity"] = identity


class _FakeContainer:
    """Test stub for DI container."""
    def __init__(self, services=None):
        self._services = services or {}
    
    def resolve(self, token, *, tag=None, optional=False):
        if token in self._services:
            return self._services[token]
        if optional:
            return None
        raise RuntimeError(f"Service {token} not registered")


def test_article_serializer_with_di():
    """
    Example test showing how to test serializers with DI defaults.
    """
    # Setup test context
    identity = _FakeIdentity(id=42, username="kai")
    request = _FakeRequest(identity=identity, client_ip="192.168.1.1")
    container = _FakeContainer()
    
    # Create serializer with DI context
    serializer = ArticleSerializer(
        data={
            "title": "Test Article",
            "content": "This is test content...",
        },
        context={
            "request": request,
            "identity": identity,
            "container": container,
        }
    )
    
    # Validate
    assert serializer.is_valid(), serializer.errors
    
    # Check DI defaults were resolved
    validated = serializer.validated_data
    assert validated["author_id"] == 42  # From CurrentUserDefault
    assert validated["tenant_id"] is None  # No tenant in test
    assert "created_at" in validated  # From CurrentTimestampDefault


def test_moderated_content_with_service():
    """
    Test serializer with injected service.
    """
    identity = _FakeIdentity(id=10)
    request = _FakeRequest(identity=identity)
    
    # Create mock moderation service
    moderator = ModerationService()
    container = _FakeContainer({ModerationService: moderator})
    
    # Test banned content
    serializer = ModeratedContentSerializer(
        data={
            "title": "Legitimate Title",
            "content": "This is spam content",  # Should fail
        },
        context={
            "request": request,
            "identity": identity,
            "container": container,
        }
    )
    
    assert not serializer.is_valid()
    assert "content" in serializer.errors
    
    # Test allowed content
    serializer2 = ModeratedContentSerializer(
        data={
            "title": "Good Title",
            "content": "This is legitimate content",
        },
        context={
            "request": request,
            "identity": identity,
            "container": container,
        }
    )
    
    assert serializer2.is_valid()


# ============================================================================
# 8. Advanced Patterns: Async Factory Methods
# ============================================================================

async def example_controller_usage():
    """
    Example showing how to use serializers in controller handlers.
    """
    from aquilia import Controller, POST
    
    class AdvancedController(Controller):
        """Controller demonstrating advanced serializer patterns."""
        
        @POST("/articles")
        async def create_article(
            self,
            ctx,
            article_ser: ArticleSerializer,  # FastAPI-style injection
        ):
            """
            The serializer is automatically:
            1. Created from request body
            2. Wired with request context and DI container
            3. Validated (is_valid(raise_fault=True))
            4. Injected with all DI defaults resolved
            """
            # article_ser.validated_data includes:
            # - author_id: Auto from CurrentUserDefault
            # - tenant_id: Auto from TenantIdDefault
            # - created_at: Auto from CurrentTimestampDefault
            # - created_ip: Auto from CurrentRequestDefault
            
            # Save to database
            article = await Article.objects.create(**article_ser.validated_data)
            
            # Return serialized response
            return ArticleSerializer(instance=article).data
        
        @POST("/articles/async")
        async def create_article_async(self, ctx):
            """
            Alternative: Use from_request_async() factory.
            """
            # Manually create serializer with from_request_async
            serializer = await ArticleSerializer.from_request_async(
                ctx.request,
                container=ctx.container,
            )
            
            # Validate
            serializer.is_valid(raise_fault=True)
            
            # Save
            article = await Article.objects.create(**serializer.validated_data)
            
            return ArticleSerializer(instance=article).data


# ============================================================================
# Summary: Key Features Demonstrated
# ============================================================================

"""
This file demonstrates:

1. **Custom DI-Aware Defaults**
   - CurrentTimestampDefault: Inject timestamps with optional service
   - TenantIdDefault: Multi-source tenant resolution

2. **Nested Serializers with DI**
   - Author nested in Article
   - DI defaults work in nested contexts

3. **Serializer Inheritance**
   - AuditedSerializer base class
   - All subclasses get audit fields automatically

4. **ModelSerializer Integration**
   - DI defaults work with auto-generated fields

5. **Custom Validation with DI Services**
   - Access container via self.container
   - Inject services for validation logic

6. **SerializerProvider**
   - Register serializers in DI container
   - auto_validate flag for automatic validation

7. **Testing Patterns**
   - Mock identity, request, container
   - Test DI default resolution

8. **Advanced Controller Patterns**
   - FastAPI-style auto-injection
   - from_request_async() factory
   - Response serialization

All patterns work seamlessly with the existing Aquilia architecture
while providing Django DRF-like ergonomics with FastAPI-style DI.
"""
