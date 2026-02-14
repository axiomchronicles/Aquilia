"""
Aquilia Model Fields Package — split-module field system.

This package re-exports all fields from the original monolithic fields.py
AND adds new field types from sub-modules. Existing imports like
``from aquilia.models.fields import CharField`` continue to work.

New sub-modules:
    base      — Field base class and core API
    mixins    — NullableMixin, UniqueMixin, IndexedMixin, ChoiceMixin, EncryptedMixin
    primitives— IntegerField, FloatField, CharField, etc.
    relation  — ForeignKey, OneToOneField, ManyToManyField
    file      — FileField, ImageField with storage hooks
    json_field— JSONField with schema validation
    composite — CompositeField, CompositePrimaryKey, CompositeAttribute
    uuid_field— Enhanced UUIDField
    binary_field— Enhanced BinaryField
    auto_field— AutoField, BigAutoField
    enum_field— EnumField
"""

# ── Re-export everything from the original monolithic fields.py ──────────────
# This keeps backward compatibility: ``from aquilia.models.fields import X``
# works whether X lives in the old fields.py or new sub-modules.

from ..fields_module import (
    # Base
    Field,
    FieldValidationError,
    Index,
    UniqueConstraint,
    UNSET,
    _Unset,
    # Numeric
    AutoField,
    BigAutoField,
    IntegerField,
    BigIntegerField,
    SmallIntegerField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    FloatField,
    DecimalField,
    # Text
    CharField,
    TextField,
    SlugField,
    EmailField,
    URLField,
    UUIDField,
    FilePathField,
    # Date/Time
    DateField,
    TimeField,
    DateTimeField,
    DurationField,
    # Boolean
    BooleanField,
    # Binary/Special
    BinaryField,
    JSONField,
    # Relationships
    RelationField,
    ForeignKey,
    OneToOneField,
    ManyToManyField,
    # IP/Network
    GenericIPAddressField,
    InetAddressField,
    # File/Media
    FileField,
    ImageField,
    # PostgreSQL
    ArrayField,
    HStoreField,
    RangeField,
    IntegerRangeField,
    BigIntegerRangeField,
    DecimalRangeField,
    DateRangeField,
    DateTimeRangeField,
    CICharField,
    CIEmailField,
    CITextField,
    # Meta/Special
    GeneratedField,
    OrderWrt,
)

# ── New sub-module exports ───────────────────────────────────────────────────
from .mixins import (
    NullableMixin,
    UniqueMixin,
    IndexedMixin,
    AutoNowMixin,
    ChoiceMixin,
    EncryptedMixin,
)
from .composite import (
    CompositeField,
    CompositePrimaryKey,
    CompositeAttribute,
)
from .enum_field import EnumField

from .validators import (
    BaseValidator,
    ValidationError,
    MinValueValidator,
    MaxValueValidator,
    MinLengthValidator,
    MaxLengthValidator,
    RegexValidator,
    EmailValidator,
    URLValidator,
    SlugValidator,
    ProhibitNullCharactersValidator,
    DecimalValidator,
    FileExtensionValidator,
    StepValueValidator,
    RangeValidator,
)

from .lookups import (
    Lookup,
    Exact,
    IExact,
    Contains,
    IContains,
    StartsWith,
    IStartsWith,
    EndsWith,
    IEndsWith,
    In,
    Gt,
    Gte,
    Lt,
    Lte,
    IsNull,
    Range,
    Regex,
    IRegex,
    register_lookup,
    resolve_lookup,
    lookup_registry,
)

__all__ = [
    # Base
    "Field",
    "FieldValidationError",
    "Index",
    "UniqueConstraint",
    "UNSET",
    # Numeric
    "AutoField",
    "BigAutoField",
    "IntegerField",
    "BigIntegerField",
    "SmallIntegerField",
    "PositiveIntegerField",
    "PositiveSmallIntegerField",
    "FloatField",
    "DecimalField",
    # Text
    "CharField",
    "TextField",
    "SlugField",
    "EmailField",
    "URLField",
    "UUIDField",
    "FilePathField",
    # Date/Time
    "DateField",
    "TimeField",
    "DateTimeField",
    "DurationField",
    # Boolean
    "BooleanField",
    # Binary/Special
    "BinaryField",
    "JSONField",
    # Relationships
    "RelationField",
    "ForeignKey",
    "OneToOneField",
    "ManyToManyField",
    # IP/Network
    "GenericIPAddressField",
    "InetAddressField",
    # File/Media
    "FileField",
    "ImageField",
    # PostgreSQL
    "ArrayField",
    "HStoreField",
    "RangeField",
    "IntegerRangeField",
    "BigIntegerRangeField",
    "DecimalRangeField",
    "DateRangeField",
    "DateTimeRangeField",
    "CICharField",
    "CIEmailField",
    "CITextField",
    # Meta/Special
    "GeneratedField",
    "OrderWrt",
    # New sub-module exports
    "NullableMixin",
    "UniqueMixin",
    "IndexedMixin",
    "AutoNowMixin",
    "ChoiceMixin",
    "EncryptedMixin",
    "CompositeField",
    "CompositePrimaryKey",
    "CompositeAttribute",
    "EnumField",
    # Validators
    "BaseValidator",
    "ValidationError",
    "MinValueValidator",
    "MaxValueValidator",
    "MinLengthValidator",
    "MaxLengthValidator",
    "RegexValidator",
    "EmailValidator",
    "URLValidator",
    "SlugValidator",
    "ProhibitNullCharactersValidator",
    "DecimalValidator",
    "FileExtensionValidator",
    "StepValueValidator",
    "RangeValidator",
    # Lookups
    "Lookup",
    "Exact",
    "IExact",
    "Contains",
    "IContains",
    "StartsWith",
    "IStartsWith",
    "EndsWith",
    "IEndsWith",
    "In",
    "Gt",
    "Gte",
    "Lt",
    "Lte",
    "IsNull",
    "Range",
    "Regex",
    "IRegex",
    "register_lookup",
    "resolve_lookup",
    "lookup_registry",
]
