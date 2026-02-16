"""
Blogs module serializers - DRF-style with DI integration.

This demonstrates all the new DI-serializer features:
- DI-aware defaults (CurrentUserDefault, CurrentRequestDefault, InjectDefault)
- Enhanced validators (RangeValidator, CompoundValidator, ConditionalValidator)
- FastAPI-style auto-injection in controller handlers
- Response serialization
"""

from aquilia import (
    Serializer,
    CharField,
    IntegerField,
    DateTimeField,
    EmailField,
    BooleanField,
    HiddenField,
    ReadOnlyField,
    SerializerIntegerField,
    SerializerDateTimeField,
    SerializerCharField,
    SerializerBooleanField,
    SerializerEmailField,
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


class BlogPostSerializer(Serializer):
    """
    Serializer for blog posts with DI-aware defaults.
    
    Demonstrates:
    - CurrentUserDefault: Auto-inject authenticated user ID
    - CurrentRequestDefault: Capture client IP for audit
    - Validators: CompoundValidator, RangeValidator
    - Response serialization: Auto-serialize handler returns
    """
    
    # Read-only fields (output only)
    id = SerializerIntegerField(read_only=True)
    created_at = SerializerDateTimeField(read_only=True)
    updated_at = SerializerDateTimeField(read_only=True)
    
    # Required fields
    title = SerializerCharField(
        max_length=200,
        validators=[
            CompoundValidator(
                MinLengthValidator(3),
                MaxLengthValidator(200),
            )
        ]
    )
    content = SerializerCharField(
        validators=[MinLengthValidator(10)]
    )
    
    # Optional fields
    excerpt = SerializerCharField(max_length=500, required=False, allow_null=True)
    published = SerializerBooleanField(default=False)
    view_count = SerializerIntegerField(
        default=0,
        validators=[RangeValidator(0, 1_000_000)]
    )
    
    # DI-aware defaults (automatically resolved from context)
    author_id = HiddenField(
        default=CurrentUserDefault(),
        # This automatically injects the current user's ID from:
        # 1. ctx.request.state["identity"]
        # 2. ctx["identity"] 
        # 3. container.resolve("identity")
    )
    
    client_ip = HiddenField(
        default=CurrentRequestDefault(attr="client_ip"),
        # Injects request.client_ip for audit logging
    )
    
    def validate_title(self, value: str) -> str:
        """Custom field validation for title."""
        if value.lower().startswith("draft"):
            raise ValueError("Title cannot start with 'draft'")
        return value
    
    def validate(self, attrs: dict) -> dict:
        """Cross-field validation."""
        # If published, excerpt is required
        if attrs.get("published") and not attrs.get("excerpt"):
            raise ValueError("Published posts must have an excerpt")
        return attrs


class BlogCommentSerializer(Serializer):
    """
    Serializer for blog comments with conditional validation.
    
    Demonstrates:
    - ConditionalValidator: Validate email only if notify_reply is True
    - InjectDefault: Inject service from DI container
    """
    
    id = SerializerIntegerField(read_only=True)
    post_id = SerializerIntegerField()
    author_name = SerializerCharField(max_length=100)
    content = SerializerCharField(
        validators=[
            CompoundValidator(
                MinLengthValidator(5),
                MaxLengthValidator(1000),
            )
        ]
    )
    
    # Conditional fields
    notify_reply = SerializerBooleanField(default=False)
    email = SerializerEmailField(
        required=False,
        validators=[
            # Only validate email if user wants notifications
            ConditionalValidator(
                condition=lambda data: data.get("notify_reply") is True,
                validator=MinLengthValidator(5),
            )
        ]
    )
    
    # DI-aware: auto-inject authenticated user
    commenter_id = HiddenField(
        default=CurrentUserDefault(use_id=True),
        required=False,  # Allow anonymous comments
    )
    
    # DI-aware: inject moderation service
    # moderation_score = HiddenField(
    #     default=InjectDefault("ModerationService", method="calculate_score")
    # )
    
    created_at = SerializerDateTimeField(read_only=True)


class BlogPostUpdateSerializer(Serializer):
    """
    Serializer for partial blog post updates.
    
    All fields optional for PATCH operations.
    """
    
    title = SerializerCharField(max_length=200, required=False)
    content = SerializerCharField(required=False)
    excerpt = SerializerCharField(max_length=500, required=False, allow_null=True)
    published = SerializerBooleanField(required=False)
    
    # Track who made the update
    updated_by = HiddenField(
        default=CurrentUserDefault()
    )


class BlogPostListSerializer(Serializer):
    """
    Lightweight serializer for listing posts (no content).
    """
    
    id = SerializerIntegerField(read_only=True)
    title = SerializerCharField(max_length=200)
    excerpt = SerializerCharField(max_length=500, allow_null=True)
    author_id = SerializerIntegerField(read_only=True)
    published = SerializerBooleanField(read_only=True)
    view_count = SerializerIntegerField(read_only=True)
    created_at = SerializerDateTimeField(read_only=True)


class BlogStatisticsSerializer(Serializer):
    """
    Serializer with service injection for computed fields.
    
    Demonstrates InjectDefault for resolving services.
    """
    
    total_posts = SerializerIntegerField(read_only=True)
    published_posts = SerializerIntegerField(read_only=True)
    total_views = SerializerIntegerField(read_only=True)
    total_comments = SerializerIntegerField(read_only=True)
    
    # Inject analytics service from DI container
    # analytics_data = HiddenField(
    #     default=InjectDefault("AnalyticsService")
    # )


class PaginatedBlogListSerializer(Serializer):
    """
    Paginated response wrapper.
    """
    
    items = ReadOnlyField()  # Will be a list of BlogPostListSerializer
    total = SerializerIntegerField(read_only=True)
    page = SerializerIntegerField(read_only=True)
    page_size = SerializerIntegerField(read_only=True)
    has_next = SerializerBooleanField(read_only=True)
