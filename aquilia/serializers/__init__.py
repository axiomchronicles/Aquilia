"""
Aquilia Serializers — Production-grade DRF-inspired serialization system.

Provides:
- Serializer: Base serializer with declarative field definitions
- ModelSerializer: Auto-generates fields from Aquilia Model classes
- ListSerializer: Handles lists of objects
- Fields: Full field type library with validation & coercion
- Relations: PrimaryKeyRelatedField, SlugRelatedField, StringRelatedField
- Validators: UniqueValidator, UniqueTogetherValidator
- Faults: Integrated with Aquilia's fault domain system

Usage::

    from aquilia.serializers import Serializer, ModelSerializer
    from aquilia.serializers.fields import CharField, IntegerField, EmailField

    class UserSerializer(Serializer):
        name = CharField(max_length=150)
        email = EmailField()
        age = IntegerField(min_value=0, required=False)

    class ProductSerializer(ModelSerializer):
        class Meta:
            model = Product
            fields = "__all__"
            exclude = ["internal_notes"]
            read_only_fields = ["id", "created_at"]

    # Deserialize (validate incoming data)
    s = UserSerializer(data={"name": "Kai", "email": "kai@aquilia.dev"})
    if s.is_valid():
        cleaned = s.validated_data
    else:
        errors = s.errors

    # Serialize (render outgoing data)
    s = UserSerializer(instance=user_obj)
    output = s.data
"""

from .base import (
    Serializer,
    ModelSerializer,
    ListSerializer,
    SerializerMeta,
)

from .fields import (
    # Base
    SerializerField,
    # Primitives
    BooleanField,
    NullBooleanField,
    CharField,
    EmailField,
    SlugField,
    URLField,
    UUIDField,
    IPAddressField,
    # Numeric
    IntegerField,
    FloatField,
    DecimalField,
    # Date/Time
    DateField,
    TimeField,
    DateTimeField,
    DurationField,
    # Structured
    ListField,
    DictField,
    JSONField,
    # Special
    ReadOnlyField,
    HiddenField,
    SerializerMethodField,
    ChoiceField,
    MultipleChoiceField,
    FileField,
    ImageField,
    # Constant
    ConstantField,
)

from .relations import (
    RelatedField,
    PrimaryKeyRelatedField,
    SlugRelatedField,
    StringRelatedField,
)

from .validators import (
    UniqueValidator,
    UniqueTogetherValidator,
    MaxLengthValidator,
    MinLengthValidator,
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)

from .exceptions import (
    SerializationFault,
    ValidationFault,
    FieldValidationFault,
)

__all__ = [
    # Core
    "Serializer",
    "ModelSerializer",
    "ListSerializer",
    "SerializerMeta",
    # Fields
    "SerializerField",
    "BooleanField",
    "NullBooleanField",
    "CharField",
    "EmailField",
    "SlugField",
    "URLField",
    "UUIDField",
    "IPAddressField",
    "IntegerField",
    "FloatField",
    "DecimalField",
    "DateField",
    "TimeField",
    "DateTimeField",
    "DurationField",
    "ListField",
    "DictField",
    "JSONField",
    "ReadOnlyField",
    "HiddenField",
    "SerializerMethodField",
    "ChoiceField",
    "MultipleChoiceField",
    "FileField",
    "ImageField",
    "ConstantField",
    # Relations
    "RelatedField",
    "PrimaryKeyRelatedField",
    "SlugRelatedField",
    "StringRelatedField",
    # Validators
    "UniqueValidator",
    "UniqueTogetherValidator",
    "MaxLengthValidator",
    "MinLengthValidator",
    "MaxValueValidator",
    "MinValueValidator",
    "RegexValidator",
    # Faults
    "SerializationFault",
    "ValidationFault",
    "FieldValidationFault",
]
