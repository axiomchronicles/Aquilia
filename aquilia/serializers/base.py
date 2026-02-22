"""
Aquilia Serializer Core — Serializer, ModelSerializer, ListSerializer.

The heart of Aquilia's serialization layer.  Provides:

- ``Serializer``: Declarative field-based serializer with full validation
- ``ModelSerializer``: Auto-generates fields from an Aquilia ``Model`` class
- ``ListSerializer``: Handles serialization/deserialization of collections

Architecture:
    SerializerMeta (metaclass)
    └── Serializer (base)
        ├── ModelSerializer (auto-fields from Model)
        └── ListSerializer (many=True wrapper)

Usage::

    class UserSerializer(Serializer):
        name = CharField(max_length=150)
        email = EmailField()
        age = IntegerField(required=False, default=0)

    # Deserialize (input validation)
    s = UserSerializer(data={"name": "Kai", "email": "kai@aq.dev"})
    if s.is_valid():
        user_data = s.validated_data  # {"name": "Kai", "email": "kai@aq.dev", "age": 0}

    # Serialize (output rendering)
    s = UserSerializer(instance=user_obj)
    output = s.data  # {"name": "Kai", "email": "kai@aq.dev", "age": 25}
"""

from __future__ import annotations

import copy
import datetime
import decimal
import uuid
from collections import OrderedDict
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

# ============================================================================
# Serialization Plan — precomputed per-class for O(1) field iteration
# ============================================================================

class _FieldPlanEntry:
    """Precomputed metadata for a single field in a serialization plan.

    Uses __slots__ to minimize per-entry allocation overhead.
    """
    __slots__ = ('name', 'field', 'write_only', 'read_only', 'source_star',
                 'required', 'has_default', 'is_di_default_flag')

    def __init__(self, name: str, field: Any) -> None:
        self.name = name
        self.field = field
        self.write_only = field.write_only
        self.read_only = field.read_only
        self.source_star = (field.source == '*')
        self.required = field.required
        self.has_default = field.default is not _empty_sentinel
        self.is_di_default_flag = False


# Sentinel — resolved after fields import
_empty_sentinel = None  # Set below after import


def _build_representation_plan(fields: dict) -> tuple:
    """Build a tuple of (name, field, source_star) for non-write-only fields.

    Called once per serializer class to avoid per-request dict iteration.
    """
    plan = []
    for name, field in fields.items():
        if not field.write_only:
            plan.append((name, field, field.source == '*'))
    return tuple(plan)


def _build_validation_plan(fields: dict) -> tuple:
    """Build a tuple of (name, field) for non-read-only fields."""
    plan = []
    for name, field in fields.items():
        if not field.read_only:
            plan.append((name, field))
    return tuple(plan)

from .fields import (
    SerializerField,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    DecimalField,
    DurationField,
    EmailField,
    FloatField,
    IntegerField,
    JSONField,
    ListField,
    ReadOnlyField,
    SlugField,
    TimeField,
    URLField,
    UUIDField,
    empty,
    is_di_default,
)
from .relations import PrimaryKeyRelatedField, StringRelatedField
from .exceptions import SerializationFault, ValidationFault

# Resolve sentinel now that empty is imported
_empty_sentinel = empty


# ============================================================================
# Metaclass
# ============================================================================

class SerializerMeta(type):
    """
    Metaclass for Serializer classes.

    Collects declared ``SerializerField`` instances from the class body
    and parent classes into ``_declared_fields`` (ordered dict).

    Optimization: Uses plain dict (Python 3.7+ guarantees insertion order)
    instead of OrderedDict to reduce overhead.
    """

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> SerializerMeta:
        # Collect fields from this class
        declared: list[tuple[str, SerializerField]] = []
        for key, value in list(namespace.items()):
            if isinstance(value, type) and issubclass(value, SerializerField):
                # Auto-instantiate if a class was provided (e.g. name = NameSerializer)
                value = value()
            
            if isinstance(value, SerializerField):
                declared.append((key, value))
                namespace.pop(key)

        # Sort by creation order
        declared.sort(key=lambda pair: pair[1]._order)

        # Inherit parent fields
        parent_fields: dict[str, SerializerField] = {}
        for base in reversed(bases):
            if hasattr(base, "_declared_fields"):
                parent_fields.update(base._declared_fields)

        # Merge: parent fields first, then this class's fields (override)
        all_fields = dict(parent_fields)
        for field_name, field_obj in declared:
            all_fields[field_name] = field_obj

        namespace["_declared_fields"] = all_fields

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        return cls


# ============================================================================
# Serializer
# ============================================================================

class Serializer(SerializerField, metaclass=SerializerMeta):
    """
    Base serializer with declarative field-based validation.

    Modes:
        - **Serialization** (output): Pass ``instance=obj``, read ``.data``
        - **Deserialization** (input): Pass ``data=dict``, call ``.is_valid()``,
          then read ``.validated_data``
        - **Both**: Pass both ``instance`` and ``data`` for update scenarios

    Options:
        - ``partial=True``: Allow partial updates (missing fields OK)
        - ``many=True``: Wrap with ``ListSerializer``
        - ``context=dict``: Extra context (e.g. request) available to fields
    """

    _declared_fields: ClassVar[dict[str, SerializerField]]

    # Class-level caches (populated lazily)
    _repr_plan: ClassVar[tuple | None] = None
    _valid_plan: ClassVar[tuple | None] = None
    _validate_methods: ClassVar[dict[str, Any] | None] = None

    class Meta:
        """Override in subclasses for configuration."""
        pass

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        # Automatically delegate to ListSerializer if many=True
        if kwargs.pop("many", False):
            return cls.many(*args, **kwargs)
        return super().__new__(cls)

    def __init__(
        self,
        instance: Any = None,
        data: Any = empty,
        *,
        partial: bool = False,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        # Initialize SerializerField base
        super().__init__(**kwargs)

        self.instance = instance
        self.initial_data = data
        self.partial = partial
        self.context = context or {}
        self._validated_data: Any = empty
        self._errors: dict[str, list[str]] = {}
        self._data: Any = None

        # Bind fields to this serializer instance
        # Optimization: use shallow copy + rebind instead of deepcopy
        # This is safe because fields are stateless between serializations;
        # only field_name, parent, source, label, and _source_parts are mutated by bind().
        self.fields: dict[str, SerializerField] = {}
        for name, field in self._declared_fields.items():
            field_copy = copy.copy(field)
            field_copy.validators = list(field.validators)  # shallow copy validator list
            field_copy.error_messages = dict(field.error_messages)  # shallow copy messages
            field_copy.bind(name, self)
            self.fields[name] = field_copy

        # Cache validate_* method references (avoid getattr per field per request)
        cls = type(self)
        if cls._validate_methods is None:
            methods: dict[str, Any] = {}
            for fname in self._declared_fields:
                m = getattr(cls, f"validate_{fname}", None)
                if m is not None:
                    methods[fname] = m
            cls._validate_methods = methods

    # ── DI Integration ───────────────────────────────────────────────────

    @property
    def container(self) -> Any:
        """
        Get the DI container from context (if available).

        The container is automatically set when the serializer is resolved
        through the DI system or when created via ``from_request()``.
        """
        return self.context.get("container")

    @property
    def request(self) -> Any:
        """
        Get the current request from context (if available).

        Automatically set when the serializer is resolved through DI
        or when created via ``from_request()``.
        """
        return self.context.get("request")

    @classmethod
    def from_request(
        cls,
        request: Any,
        *,
        instance: Any = None,
        partial: bool = False,
        context: dict[str, Any] | None = None,
        container: Any = None,
    ) -> "Serializer":
        """
        Create a serializer pre-wired with request data and DI context.

        This is the primary factory for controller handlers — similar to
        how FastAPI automatically resolves Pydantic models from request body.

        Usage::

            @POST("/users")
            async def create_user(self, ctx):
                serializer = UserSerializer.from_request(
                    ctx.request,
                    container=ctx.container,
                )
                serializer.is_valid(raise_fault=True)
                user = await serializer.save()
                return Response.json(serializer.data, status=201)

        Args:
            request: The HTTP request object.
            instance: Optional model instance for updates.
            partial: Allow partial updates.
            context: Extra context dict.
            container: DI container (auto-resolved from request if None).

        Returns:
            Serializer instance with request data bound.
        """
        import asyncio

        # Build context
        ctx = dict(context or {})
        ctx["request"] = request

        # Resolve container
        if container is None:
            # Try request.state
            state = getattr(request, "state", None)
            if state is not None:
                container = (
                    state.get("di_container")
                    if isinstance(state, dict)
                    else getattr(state, "di_container", None)
                )
        if container is not None:
            ctx["container"] = container

        # Parse request body
        data = empty
        if hasattr(request, "_body_cache"):
            # Already parsed
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                # We're in async — caller should use await
                pass
            else:
                data = asyncio.run(request.json())
        # Caller may also pass data= explicitly

        return cls(
            instance=instance,
            data=data,
            partial=partial,
            context=ctx,
        )

    @classmethod
    async def from_request_async(
        cls,
        request: Any,
        *,
        instance: Any = None,
        partial: bool = False,
        context: dict[str, Any] | None = None,
        container: Any = None,
    ) -> "Serializer":
        """
        Async factory — parse request body and create serializer.

        Usage in controller handler::

            @POST("/users")
            async def create_user(self, ctx):
                serializer = await UserSerializer.from_request_async(ctx.request)
                serializer.is_valid(raise_fault=True)
                user = await serializer.save()
                return UserSerializer(instance=user).data

        Args:
            request: The HTTP request object.
            instance: Optional model instance for updates.
            partial: Allow partial updates.
            context: Extra context dict.
            container: DI container (auto-resolved from request if None).

        Returns:
            Serializer instance with parsed request data bound.
        """
        # Build context
        ctx = dict(context or {})
        ctx["request"] = request

        # Resolve container
        if container is None:
            state = getattr(request, "state", None)
            if state is not None:
                container = (
                    state.get("di_container")
                    if isinstance(state, dict)
                    else getattr(state, "di_container", None)
                )
        if container is not None:
            ctx["container"] = container

        data = {}
        content_type = request.content_type() or ""
        
        # 1. JSON handling
        if request.is_json() or content_type.startswith("application/json"):
            try:
                data = await request.json()
            except Exception:
                # If parsing fails, pass empty/None and let validation catch it
                pass

        # 2. Form Data Handling (urlencoded or multipart)
        elif content_type.startswith(("application/x-www-form-urlencoded", "multipart/form-data")):
            try:
                if content_type.startswith("multipart/form-data"):
                    form_data = await request.multipart()
                else:
                    form_data = await request.form()
                data = {}
                
                # Identify fields that expect lists (to preserve multiple values)
                # We inspect _declared_fields to see if semantic type is ListField
                list_field_names = set()
                for name, field in cls._declared_fields.items():
                    if isinstance(field, ListField):
                        list_field_names.add(name)
                        # Also track by source if different
                        if field.source and field.source != name:
                            list_field_names.add(field.source)

                # Helper to merge items from MultiDicts (fields/files)
                def _merge_items(source: Any):
                    if not source: return
                    # source.items() yields (key, list_of_values) for MultiDict
                    for key, values in source.items():
                        if not values:
                            continue
                            
                        # If field expects a list, or we have multiple values and explicit list support
                        if key in list_field_names:
                            data[key] = values
                        else:
                            # Standard fields (Char, Int, etc) expect a single scalar.
                            # Take the first value from the MultiDict list.
                            data[key] = values[0]

                if hasattr(form_data, "fields"):
                    _merge_items(form_data.fields)
                    
                if hasattr(form_data, "files"):
                    _merge_items(form_data.files)
                    
            except Exception:
                pass

        # 3. Fallback / Parsing attempt
        else:
            try:
                data = await request.json()
            except Exception:
                pass

        return cls(
            instance=instance,
            data=data,
            partial=partial,
            context=ctx,
        )

    # ── many=True shortcut ───────────────────────────────────────────────

    @classmethod
    def many(
        cls,
        instance: Any = None,
        data: Any = empty,
        **kwargs: Any,
    ) -> "ListSerializer":
        """
        Shortcut for creating a ListSerializer wrapping this serializer.

        Usage::

            output = UserSerializer.many(instance=users_list).data
        """
        return ListSerializer(child=cls(), instance=instance, data=data, **kwargs)

    # ── Serialization (output) ───────────────────────────────────────────

    @property
    def data(self) -> Any:
        """
        Serialized output data.

        For serialization mode (``instance`` provided), renders
        the instance through all fields' ``to_representation``.
        For deserialization mode (after ``is_valid()``), returns
        the validated data.
        """
        if self._data is not None:
            return self._data

        if self.instance is not None:
            self._data = self.to_representation(self.instance)
        elif self._validated_data is not empty:
            self._data = self._validated_data
        else:
            self._data = {}
        return self._data

    def to_representation(self, instance: Any) -> dict:
        """
        Convert an object instance to a dict of primitives.

        Optimized: uses precomputed representation plan (tuple of
        non-write-only fields) to avoid per-call dict iteration
        and boolean checks. Uses plain dict (insertion-ordered in
        Python 3.7+) instead of OrderedDict.
        """
        result: dict[str, Any] = {}
        for field_name, field in self.fields.items():
            if field.write_only:
                continue
            try:
                source = field.source
                if source == "*":
                    # SerializerMethodField / whole-object access
                    value = instance
                elif getattr(field, '_simple_source', False):
                    # Fast path: simple (non-dotted) source
                    attr = field._source_parts[0]
                    if isinstance(instance, Mapping):
                        value = instance.get(attr)
                    else:
                        value = getattr(instance, attr, None)
                else:
                    value = field.get_attribute(instance)
                result[field_name] = field.to_representation(value)
            except Exception:
                result[field_name] = None
        return result

    # ── Deserialization (input) ──────────────────────────────────────────

    def is_valid(self, *, raise_fault: bool = False) -> bool:
        """
        Validate the input data.

        After calling, ``.validated_data`` or ``.errors`` are populated.

        Args:
            raise_fault: If True, raise ``ValidationFault`` on errors.

        Returns:
            True if data is valid, False otherwise.
        """
        if self.initial_data is empty:
            raise SerializationFault(
                code="NO_DATA",
                message="Cannot call is_valid() without passing `data=` to the serializer.",
            )

        self._errors = {}
        try:
            self._validated_data = self.run_validation(self.initial_data)
        except ValidationFault as exc:
            self._errors = exc.errors
            self._validated_data = empty

        if self._errors and raise_fault:
            raise ValidationFault(errors=self._errors)

        return not bool(self._errors)

    @property
    def validated_data(self) -> dict[str, Any]:
        """Return validated data (only available after ``is_valid()``)."""
        if self._validated_data is empty:
            raise SerializationFault(
                code="NOT_VALIDATED",
                message="You must call `.is_valid()` before accessing `.validated_data`.",
            )
        return self._validated_data

    @property
    def errors(self) -> dict[str, list[str]]:
        """Return validation errors."""
        return self._errors

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        """
        Per-field validation and extraction.
        When used as a nested serializer field, this does the parsing.
        """
        if not isinstance(data, Mapping):
            raise ValidationFault(
                errors={"__all__": ["Expected a dictionary of items."]},
            )

        result: dict[str, Any] = {}
        errors: dict[str, Any] = {}

        # --- Per-field validation ---
        for field_name, field in self.fields.items():
            if field.read_only:
                continue

            # Get raw value
            if field_name in data:
                raw = data[field_name]
            elif field.source and field.source != field_name and field.source in data:
                raw = data[field.source]
            else:
                raw = empty

            # Handle missing values
            if raw is empty:
                if self.partial:
                    continue  # Skip missing fields in partial updates
                
                if is_di_default(field.default):
                    try:
                        resolved = field.default.resolve(self.context)
                        if getattr(field.default, "_di_requires_coercion", False):
                            raw = resolved
                            # Falls through to coercion
                        else:
                            result[field_name] = resolved
                            continue
                    except Exception as exc:
                        errors[field_name] = [str(exc)]
                        continue
                elif getattr(field.source, "_is_di_default", False) or hasattr(field.source, "resolve"):
                    # Support for extractor defined in source rather than default
                    try:
                        resolved = field.source.resolve(self.context)
                        if getattr(field.source, "_di_requires_coercion", False):
                            raw = resolved
                        else:
                            result[field_name] = resolved
                            continue
                    except Exception as exc:
                        errors[field_name] = [str(exc)]
                        continue
                elif field.required:
                    errors[field_name] = [field.error_messages.get("required", "This field is required.")]
                    continue
                else:
                    try:
                        raw = field.get_default()
                    except (ValueError, RuntimeError) as exc:
                        errors[field_name] = [str(exc)]
                        continue

            # Handle null values
            if raw is None:
                if not field.allow_null:
                    errors[field_name] = [field.error_messages.get("null", "This field may not be null.")]
                    continue
                result[field_name] = None
                continue

            # Coerce + validate
            try:
                value = field.to_internal_value(raw)
                field.run_validators(value)
                value = field.validate(value)
                result[field_name] = value
            except ValidationFault as exc:
                errors[field_name] = exc.errors
            except (ValueError, TypeError) as exc:
                errors[field_name] = [str(exc)]

        if errors:
            raise ValidationFault(errors=errors)

        # --- Per-field custom validation hooks ---
        # Uses cached validate_* method references (built in __init__)
        cached_methods = type(self)._validate_methods or {}
        for field_name in list(result.keys()):
            method = cached_methods.get(field_name)
            if method is not None:
                try:
                    result[field_name] = method(self, result[field_name])
                except ValidationFault as exc:
                    errors[field_name] = exc.errors
                except (ValueError, TypeError) as exc:
                    errors.setdefault(field_name, []).append(str(exc))

        if errors:
            raise ValidationFault(errors=errors)
            
        return result

    def run_validation(self, data: Any) -> dict[str, Any]:
        """
        Top-level validation pipeline. Calls to_internal_value, then validators and validate hooks.
        """
        # 1. Per-field and custom field hooks
        value = self.to_internal_value(data)
        
        errors: dict[str, Any] = {}
        
        # 2. Run object-level validators
        try:
            self.run_validators(value)
        except (ValueError, TypeError) as exc:
            errors.setdefault("__all__", []).append(str(exc))
        except ValidationFault as exc:
            errors.update(exc.errors)

        # 3. Object-level validation
        try:
            value = self.validate(value)
        except (ValueError, TypeError) as exc:
            errors.setdefault("__all__", []).append(str(exc))
        except ValidationFault as exc:
            # If validate() raises a structured fault
            errors.update(exc.errors)

        if errors:
            raise ValidationFault(errors=errors)
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Object-level validation hook.

        Override to add cross-field validation::

            def validate(self, attrs):
                if attrs.get("password") != attrs.get("confirm_password"):
                    raise ValueError("Passwords do not match.")
                return attrs
        """
        return attrs

    # ── Create / Update Hooks ────────────────────────────────────────────

    async def create(self, validated_data: dict[str, Any]) -> Any:
        """
        Create a new object from validated data.

        Override in subclasses for persistence::

            async def create(self, validated_data):
                return await User.objects.create(**validated_data)
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.create() must be implemented."
        )

    async def update(self, instance: Any, validated_data: dict[str, Any]) -> Any:
        """
        Update an existing object from validated data.

        Override in subclasses for persistence::

            async def update(self, instance, validated_data):
                for attr, value in validated_data.items():
                    setattr(instance, attr, value)
                await instance.save()
                return instance
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.update() must be implemented."
        )

    async def save(self, **kwargs: Any) -> Any:
        """
        Persist the object using ``create()`` or ``update()``.

        Args:
            **kwargs: Extra fields to merge into validated_data.

        Returns:
            The created/updated object instance.
        """
        if self._validated_data is empty:
            raise SerializationFault(
                code="NOT_VALIDATED",
                message="You must call `.is_valid()` before calling `.save()`.",
            )

        validated = {**self._validated_data, **kwargs}

        if self.instance is not None:
            self.instance = await self.update(self.instance, validated)
        else:
            self.instance = await self.create(validated)

        return self.instance

    # ── OpenAPI Schema Generation ────────────────────────────────────────

    def to_schema(self, *, for_request: bool = False) -> Dict[str, Any]:
        """
        Generate OpenAPI JSON Schema for this serializer.

        Args:
            for_request: If True, exclude read_only fields (for request body).
                         If False, exclude write_only fields (for response).

        Returns:
            JSON Schema dictionary.
        """
        properties: Dict[str, Any] = {}
        required: list[str] = []

        for field_name, field in self.fields.items():
            if for_request and field.read_only:
                continue
            if not for_request and field.write_only:
                continue

            # Nested serializer
            if isinstance(field, Serializer):
                properties[field_name] = field.to_schema(for_request=for_request)
            else:
                properties[field_name] = field.to_schema()

            if field.required and not field.read_only:
                required.append(field_name)

        schema: Dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required and for_request:
            schema["required"] = required

        doc = getattr(self.__class__, "__doc__", None)
        if doc:
            schema["description"] = doc.strip().split("\n")[0]

        return schema

    # ── Representation ───────────────────────────────────────────────────

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        fields = ", ".join(self.fields.keys())
        return f"<{cls_name}(fields=[{fields}])>"


# ============================================================================
# ListSerializer
# ============================================================================

class ListSerializer(SerializerField):
    """
    Handles serialization/deserialization of lists of objects.

    Wraps a child ``Serializer`` and applies it to each item.

    Usage::

        s = ListSerializer(child=UserSerializer(), data=[...])
        if s.is_valid():
            users = s.validated_data  # list[dict]

        s = ListSerializer(child=UserSerializer(), instance=[user1, user2])
        output = s.data  # [{"name": ...}, {"name": ...}]
    """

    def __init__(
        self,
        *,
        child: Any,
        instance: Any = None,
        data: Any = empty,
        partial: bool = False,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        self.child = child
        super().__init__(**kwargs)
        self.instance = instance
        self.initial_data = data
        self.partial = partial
        self.context = context or {}
        self._validated_data: Any = empty
        self._errors: Any = []
        self._data: Any = None

    @property
    def data(self) -> list:
        """Serialized output: list of dicts."""
        if self._data is not None:
            return self._data
        if self.instance is not None:
            self._data = self.to_representation(self.instance)
        elif self._validated_data is not empty:
            self._data = self._validated_data
        else:
            self._data = []
        return self._data

    def to_representation(self, instances: Sequence) -> list:
        """Convert a list of objects to a list of dicts."""
        return [
            self.child.to_representation(item)
            for item in instances
        ]

    def to_internal_value(self, data: Any) -> list:
        """Process a list of input dicts."""
        if not isinstance(data, (list, tuple)):
            raise ValidationFault(errors={"__all__": ["Expected a list of items."]})

        results = []
        errors = []
        has_errors = False

        for idx, item in enumerate(data):
            # Create a fresh child for each item
            child = self.child.__class__(
                data=item, 
                partial=self.partial, 
                context=self.context
            )
            try:
                results.append(child.run_validation(item))
                errors.append({})
            except ValidationFault as exc:
                has_errors = True
                results.append({})
                errors.append(exc.errors)
            except (ValueError, TypeError) as exc:
                has_errors = True
                results.append({})
                errors.append({"__all__": [str(exc)]})

        if has_errors:
            raise ValidationFault(errors=errors)

        return results

    def is_valid(self, *, raise_fault: bool = False) -> bool:
        """Validate a list of input dicts."""
        if self.initial_data is empty:
            raise SerializationFault(
                code="NO_DATA",
                message="Cannot call is_valid() without passing `data=`.",
            )

        self._errors = []
        try:
            self._validated_data = self.to_internal_value(self.initial_data)
        except ValidationFault as exc:
            self._errors = exc.errors
            self._validated_data = empty

        if self._errors and raise_fault:
            raise ValidationFault(errors={"__all__": [f"Item {i}: {e}" for i, e in enumerate(self._errors) if e]})

        return not bool(self._errors)

    @property
    def validated_data(self) -> list[dict[str, Any]]:
        if self._validated_data is empty:
            raise SerializationFault(
                code="NOT_VALIDATED",
                message="You must call `.is_valid()` before accessing `.validated_data`.",
            )
        return self._validated_data

    @property
    def errors(self) -> list[dict[str, list[str]]]:
        return self._errors

    async def create(self, validated_data: list[dict[str, Any]]) -> list[Any]:
        """Create multiple objects."""
        results = []
        for item_data in validated_data:
            child = self.child.__class__(data=item_data, context=self.context)
            child.is_valid(raise_fault=True)
            obj = await child.create(child.validated_data)
            results.append(obj)
        return results

    async def save(self, **kwargs: Any) -> list[Any]:
        """Persist all validated items."""
        if self._validated_data is empty:
            raise SerializationFault(
                code="NOT_VALIDATED",
                message="You must call `.is_valid()` before calling `.save()`.",
            )
        return await self.create(self._validated_data)

    def to_schema(self, *, for_request: bool = False) -> Dict[str, Any]:
        """Generate OpenAPI schema for list."""
        return {
            "type": "array",
            "items": self.child.to_schema(for_request=for_request) if isinstance(self.child, Serializer) else {},
        }

    def __repr__(self) -> str:
        return f"<ListSerializer(child={self.child.__class__.__name__})>"


# ============================================================================
# Buffer Pool — reusable byte buffers to reduce allocations
# ============================================================================

class BufferPool:
    """Thread-local reusable byte buffer pool for serialization.

    Avoids repeated allocation of large buffers for JSON encoding.
    Each ``acquire()`` returns a cleared ``bytearray``; ``release()``
    returns it to the pool for reuse.

    Usage::

        pool = BufferPool(initial_size=4096, max_pool=8)
        buf = pool.acquire()
        buf.extend(b'{"key":"value"}')
        result = bytes(buf)
        pool.release(buf)

    Thread-safety: uses a simple list as a free-list. Under GIL this
    is safe for typical web-server concurrency (one coroutine at a time
    per thread). For multi-threaded use, wrap with threading.Lock.
    """

    __slots__ = ('_pool', '_initial_size', '_max_pool')

    def __init__(self, initial_size: int = 4096, max_pool: int = 16):
        self._pool: list[bytearray] = []
        self._initial_size = initial_size
        self._max_pool = max_pool

    def acquire(self) -> bytearray:
        """Get a buffer from the pool or create a new one."""
        if self._pool:
            buf = self._pool.pop()
            buf.clear()
            return buf
        buf = bytearray()
        return buf

    def release(self, buf: bytearray) -> None:
        """Return a buffer to the pool (if pool not full)."""
        if len(self._pool) < self._max_pool:
            self._pool.append(buf)

    def __repr__(self) -> str:
        return f"<BufferPool(size={self._initial_size}, pooled={len(self._pool)})>"


# Global buffer pool instance
_buffer_pool = BufferPool(initial_size=4096, max_pool=16)


def get_buffer_pool() -> BufferPool:
    """Get the global buffer pool for serializer use."""
    return _buffer_pool


# ============================================================================
# Streaming Serializer — generator-based for large JSON payloads
# ============================================================================

class StreamingSerializer:
    """Generator-based streaming serializer for large collections.

    Instead of materializing the entire JSON array in memory, yields
    encoded byte chunks suitable for streaming HTTP responses.

    Usage::

        class UserSerializer(Serializer):
            name = CharField()
            email = EmailField()

        streamer = StreamingSerializer(
            child=UserSerializer(),
            instance=large_user_queryset,
            chunk_size=32768,
        )

        # In an ASGI response:
        async def response_body():
            for chunk in streamer.stream():
                yield chunk

    Args:
        child: The serializer to apply to each item.
        instance: An iterable of objects to serialize.
        chunk_size: Target chunk size in bytes (default 32KB).
        json_encoder: Optional custom JSON encoder function.
    """

    __slots__ = ('child', 'instance', 'chunk_size', '_json_encode')

    def __init__(
        self,
        *,
        child: Serializer,
        instance: Any,
        chunk_size: int = 32768,
        json_encoder: Any = None,
    ):
        self.child = child
        self.instance = instance
        self.chunk_size = chunk_size

        # Resolve JSON encoder
        if json_encoder is not None:
            self._json_encode = json_encoder
        else:
            try:
                import orjson as _orjson
                self._json_encode = _orjson.dumps
            except ImportError:
                import json as _json
                self._json_encode = lambda obj: _json.dumps(obj).encode('utf-8')

    def stream(self):
        """Yield encoded byte chunks for a JSON array of serialized items.

        Yields:
            bytes: Encoded JSON chunks. The complete output forms a valid
            JSON array ``[item1, item2, ...]``.
        """
        pool = get_buffer_pool()
        buf = pool.acquire()
        buf.extend(b'[')
        first = True

        for item in self.instance:
            data = self.child.to_representation(item)
            encoded = self._json_encode(data)
            if isinstance(encoded, str):
                encoded = encoded.encode('utf-8')

            if not first:
                buf.extend(b',')
            first = False

            buf.extend(encoded)

            if len(buf) >= self.chunk_size:
                yield bytes(buf)
                buf.clear()

        buf.extend(b']')
        yield bytes(buf)
        pool.release(buf)

    async def stream_async(self):
        """Async version of stream() for async iterables.

        Yields:
            bytes: Encoded JSON chunks.
        """
        pool = get_buffer_pool()
        buf = pool.acquire()
        buf.extend(b'[')
        first = True

        async_iter = self.instance.__aiter__() if hasattr(self.instance, '__aiter__') else None
        if async_iter is not None:
            async for item in self.instance:
                data = self.child.to_representation(item)
                encoded = self._json_encode(data)
                if isinstance(encoded, str):
                    encoded = encoded.encode('utf-8')

                if not first:
                    buf.extend(b',')
                first = False

                buf.extend(encoded)

                if len(buf) >= self.chunk_size:
                    yield bytes(buf)
                    buf.clear()
        else:
            for item in self.instance:
                data = self.child.to_representation(item)
                encoded = self._json_encode(data)
                if isinstance(encoded, str):
                    encoded = encoded.encode('utf-8')

                if not first:
                    buf.extend(b',')
                first = False

                buf.extend(encoded)

                if len(buf) >= self.chunk_size:
                    yield bytes(buf)
                    buf.clear()

        buf.extend(b']')
        yield bytes(buf)
        pool.release(buf)

    def __repr__(self) -> str:
        return f"<StreamingSerializer(child={self.child.__class__.__name__}, chunk_size={self.chunk_size})>"


# ============================================================================
# JSON Backend Configuration
# ============================================================================

class SerializerConfig:
    """Global serializer configuration.

    Controls JSON backend, buffer sizes, and feature flags.

    Usage::

        from aquilia.serializers.base import SerializerConfig

        SerializerConfig.json_backend = "orjson"  # or "ujson", "stdlib"
        SerializerConfig.buffer_pool_size = 32
        SerializerConfig.enable_plan_cache = True
    """

    # JSON backend: "orjson" | "ujson" | "stdlib" | "auto"
    json_backend: str = "auto"

    # Buffer pool settings
    buffer_pool_size: int = 16
    buffer_initial_size: int = 4096

    # Feature flags
    enable_plan_cache: bool = True
    enable_streaming: bool = True

    # Resolved encoder (cached)
    _encoder: Any = None
    _decoder: Any = None

    @classmethod
    def get_json_encoder(cls):
        """Get the configured JSON encoder function.

        Returns:
            A callable that takes a Python object and returns bytes.
        """
        if cls._encoder is not None:
            return cls._encoder

        backend = cls.json_backend

        if backend == "auto":
            try:
                import orjson
                cls._encoder = orjson.dumps
                return cls._encoder
            except ImportError:
                pass
            try:
                import ujson
                cls._encoder = lambda obj: ujson.dumps(obj).encode('utf-8')
                return cls._encoder
            except ImportError:
                pass
            import json
            cls._encoder = lambda obj: json.dumps(obj).encode('utf-8')
            return cls._encoder

        elif backend == "orjson":
            import orjson
            cls._encoder = orjson.dumps
            return cls._encoder

        elif backend == "ujson":
            import ujson
            cls._encoder = lambda obj: ujson.dumps(obj).encode('utf-8')
            return cls._encoder

        else:  # "stdlib"
            import json
            cls._encoder = lambda obj: json.dumps(obj).encode('utf-8')
            return cls._encoder

    @classmethod
    def get_json_decoder(cls):
        """Get the configured JSON decoder function.

        Returns:
            A callable that takes bytes/str and returns a Python object.
        """
        if cls._decoder is not None:
            return cls._decoder

        backend = cls.json_backend

        if backend == "auto":
            try:
                import orjson
                cls._decoder = orjson.loads
                return cls._decoder
            except ImportError:
                pass
            try:
                import ujson
                cls._decoder = ujson.loads
                return cls._decoder
            except ImportError:
                pass
            import json
            cls._decoder = json.loads
            return cls._decoder

        elif backend == "orjson":
            import orjson
            cls._decoder = orjson.loads
            return cls._decoder

        elif backend == "ujson":
            import ujson
            cls._decoder = ujson.loads
            return cls._decoder

        else:
            import json
            cls._decoder = json.loads
            return cls._decoder

    @classmethod
    def reset(cls):
        """Reset cached encoder/decoder (call after changing json_backend)."""
        cls._encoder = None
        cls._decoder = None

# Maps Aquilia Model field class names → Serializer field classes
_MODEL_FIELD_MAP: Dict[str, Type[SerializerField]] = {
    # Text
    "CharField": CharField,
    "TextField": CharField,
    "SlugField": SlugField,
    "EmailField": EmailField,
    "URLField": URLField,
    "UUIDField": UUIDField,
    "FilePathField": CharField,
    # Numeric
    "IntegerField": IntegerField,
    "BigIntegerField": IntegerField,
    "SmallIntegerField": IntegerField,
    "PositiveIntegerField": IntegerField,
    "PositiveSmallIntegerField": IntegerField,
    "FloatField": FloatField,
    "DecimalField": DecimalField,
    "AutoField": IntegerField,
    "BigAutoField": IntegerField,
    # Boolean
    "BooleanField": BooleanField,
    # Date/Time
    "DateField": DateField,
    "TimeField": TimeField,
    "DateTimeField": DateTimeField,
    "DurationField": DurationField,
    # Binary / Special
    "BinaryField": CharField,
    "JSONField": JSONField,
    # IP
    "GenericIPAddressField": CharField,
    "InetAddressField": CharField,
    # Files
    "FileField": CharField,
    "ImageField": CharField,
    # Arrays / PostgreSQL
    "ArrayField": ListField,
    "HStoreField": JSONField,
    "RangeField": CharField,
    "GeneratedField": ReadOnlyField,
}


def _build_serializer_field(
    model_field: Any,
    read_only: bool = False,
    extra_kwargs: dict[str, Any] | None = None,
) -> SerializerField:
    """
    Convert an Aquilia Model field into a Serializer field.

    Args:
        model_field: An Aquilia ``Field`` instance from the model.
        read_only: Force the serializer field to be read-only.
        extra_kwargs: Extra keyword arguments for the serializer field.

    Returns:
        A configured ``SerializerField`` instance.
    """
    field_cls_name = type(model_field).__name__
    serializer_cls = _MODEL_FIELD_MAP.get(field_cls_name, CharField)

    kwargs: dict[str, Any] = {}

    # Transfer common attrs
    if getattr(model_field, "null", False):
        kwargs["allow_null"] = True
    if getattr(model_field, "blank", False):
        kwargs["allow_blank"] = True
    if getattr(model_field, "help_text", ""):
        kwargs["help_text"] = model_field.help_text

    # Default value
    from .fields import empty as _empty
    field_default = getattr(model_field, "default", _empty)
    _UNSET = None
    try:
        from ..models.fields_module import UNSET
        _UNSET = UNSET
    except ImportError:
        pass
    if field_default is not _UNSET and field_default is not _empty:
        if not callable(field_default):
            kwargs["default"] = field_default
        else:
            kwargs["default"] = field_default

    # Choices
    if getattr(model_field, "choices", None):
        return ChoiceField(
            choices=model_field.choices,
            read_only=read_only,
            **kwargs,
            **(extra_kwargs or {}),
        )

    # String length
    if hasattr(model_field, "max_length") and model_field.max_length and serializer_cls in (CharField, SlugField, EmailField, URLField):
        kwargs["max_length"] = model_field.max_length

    # Decimal precision
    if field_cls_name == "DecimalField":
        if hasattr(model_field, "max_digits") and model_field.max_digits:
            kwargs["max_digits"] = model_field.max_digits
        if hasattr(model_field, "decimal_places") and model_field.decimal_places is not None:
            kwargs["decimal_places"] = model_field.decimal_places

    # Numeric constraints
    if hasattr(model_field, "min_value") and model_field.min_value is not None:
        kwargs["min_value"] = model_field.min_value
    if hasattr(model_field, "max_value") and model_field.max_value is not None:
        kwargs["max_value"] = model_field.max_value

    # Read-only / auto fields
    if read_only or getattr(model_field, "primary_key", False):
        kwargs["read_only"] = True
    if not getattr(model_field, "editable", True):
        kwargs["read_only"] = True

    # Auto-now fields are always read-only
    if getattr(model_field, "auto_now", False) or getattr(model_field, "auto_now_add", False):
        kwargs["read_only"] = True

    # Required
    if not kwargs.get("read_only", False):
        has_default = getattr(model_field, "has_default", lambda: False)
        if callable(has_default):
            has_default = has_default()
        if getattr(model_field, "null", False) or getattr(model_field, "blank", False) or has_default:
            kwargs["required"] = False

    if extra_kwargs:
        kwargs.update(extra_kwargs)

    return serializer_cls(**kwargs)


# Import ChoiceField here to avoid circular import at top
from .fields import ChoiceField


# ============================================================================
# ModelSerializer
# ============================================================================

class ModelSerializer(Serializer):
    """
    Automatically generates serializer fields from an Aquilia ``Model``.

    Configuration via inner ``Meta`` class::

        class ProductSerializer(ModelSerializer):
            class Meta:
                model = Product
                fields = "__all__"                  # or ["name", "price", ...]
                exclude = ["internal_notes"]        # fields to skip
                read_only_fields = ["id", "created_at"]
                extra_kwargs = {
                    "price": {"min_value": 0},
                }
                depth = 1                           # nested relation depth
                validators = []                     # object-level validators

    Meta options:
        model:            The Aquilia Model class
        fields:           ``"__all__"`` or list of field names
        exclude:          List of field names to exclude
        read_only_fields: List of field names to force read-only
        write_only_fields: List of field names to force write-only
        extra_kwargs:     Dict of {field_name: {kwargs}} to override
        depth:            Depth for nested relations (0 = PK only)
        validators:       Object-level validators
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        # Auto-generate fields from Meta.model if they weren't declared
        meta = getattr(self.__class__, "Meta", None)
        if meta and hasattr(meta, "model"):
            self._apply_model_fields(meta)

    def _apply_model_fields(self, meta: type) -> None:
        """Generate serializer fields from the model."""
        model = meta.model
        if model is None:
            return

        fields_option = getattr(meta, "fields", None)
        exclude_option = set(getattr(meta, "exclude", []) or [])
        read_only_fields = set(getattr(meta, "read_only_fields", []) or [])
        write_only_fields = set(getattr(meta, "write_only_fields", []) or [])
        extra_kwargs = getattr(meta, "extra_kwargs", {}) or {}
        depth = getattr(meta, "depth", 0)

        # Get model fields
        model_fields = self._get_model_fields(model)

        # Determine which fields to include
        if fields_option == "__all__":
            field_names = [f.attr_name or f.name for f in model_fields]
        elif fields_option:
            field_names = list(fields_option)
        else:
            field_names = [f.attr_name or f.name for f in model_fields]

        # Apply exclude
        field_names = [f for f in field_names if f not in exclude_option]

        # Build field map
        model_field_map = {}
        for mf in model_fields:
            name = mf.attr_name or mf.name
            model_field_map[name] = mf

        # Generate serializer fields (don't override declared fields)
        for name in field_names:
            if name in self._declared_fields:
                # Use declared field as-is
                if name not in self.fields:
                    field_copy = copy.deepcopy(self._declared_fields[name])
                    field_copy.bind(name, self)
                    self.fields[name] = field_copy
                continue

            if name in model_field_map:
                mf = model_field_map[name]
                ro = name in read_only_fields
                extra = extra_kwargs.get(name, {})

                # Handle FK / Relations
                field_type_name = type(mf).__name__
                if field_type_name in ("ForeignKey", "OneToOneField"):
                    if depth > 0:
                        # Nested representation — use a ReadOnlyField for now
                        ser_field = ReadOnlyField()
                    else:
                        ser_field = PrimaryKeyRelatedField(read_only=ro, **extra)
                elif field_type_name == "ManyToManyField":
                    ser_field = PrimaryKeyRelatedField(many=True, read_only=True)
                else:
                    ser_field = _build_serializer_field(mf, read_only=ro, extra_kwargs=extra)

                # Apply write_only
                if name in write_only_fields:
                    ser_field.write_only = True

                ser_field.bind(name, self)
                self.fields[name] = ser_field

    def _get_model_fields(self, model: type) -> list:
        """Extract field objects from an Aquilia Model class."""
        # Aquilia models store fields in _meta.fields or via __dict__
        meta = getattr(model, "_meta", None)
        if meta and hasattr(meta, "fields"):
            return list(meta.fields)

        # Fallback: scan class for Field instances
        from ..models.fields_module import Field as ModelField
        fields = []
        for attr_name in dir(model):
            if attr_name.startswith("_"):
                continue
            val = getattr(model, attr_name, None)
            if isinstance(val, ModelField):
                fields.append(val)
        return sorted(fields, key=lambda f: getattr(f, "_order", 0))

    # ── CRUD Hooks ───────────────────────────────────────────────────────

    async def create(self, validated_data: dict[str, Any]) -> Any:
        """Create a model instance from validated data."""
        meta = getattr(self.__class__, "Meta", None)
        if meta and hasattr(meta, "model"):
            model = meta.model
            instance = model(**validated_data)
            await instance.save()
            return instance
        raise SerializationFault(
            code="NO_MODEL",
            message="ModelSerializer.create() requires Meta.model to be set.",
        )

    async def update(self, instance: Any, validated_data: dict[str, Any]) -> Any:
        """Update a model instance from validated data."""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        await instance.save(update_fields=list(validated_data.keys()))
        return instance

    # ── Schema Generation ────────────────────────────────────────────────

    def to_schema(self, *, for_request: bool = False) -> Dict[str, Any]:
        """Generate OpenAPI schema from model + field info."""
        schema = super().to_schema(for_request=for_request)
        meta = getattr(self.__class__, "Meta", None)
        if meta and hasattr(meta, "model"):
            schema["title"] = meta.model.__name__
        return schema
