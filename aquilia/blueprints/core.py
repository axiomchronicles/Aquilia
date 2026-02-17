"""
Aquilia Blueprint Core — the Blueprint metaclass and base class.

A Blueprint is a contract between a Model and the outside world.
It declares what the world sees (Facets), what it can send (Casts),
how integrity is enforced (Seals), and how data is written back (Imprints).

This is NOT a serializer. It is a *first-class framework primitive*.
"""

from __future__ import annotations

import copy
import inspect
from typing import (
    Any,
    Dict,
    FrozenSet,
    List,
    Optional,
    Sequence,
    Set,
    Type,
    TYPE_CHECKING,
)

from .facets import Facet, UNSET, derive_facet, Computed, Constant, ReadOnly, Inject
from .lenses import Lens, _ProjectedRef
from .projections import ProjectionRegistry
from .exceptions import (
    BlueprintFault,
    CastFault,
    SealFault,
    ImprintFault,
    ProjectionFault,
)

if TYPE_CHECKING:
    from ..models.base import Model


__all__ = ["Blueprint", "BlueprintMeta"]


# ── Spec Descriptor ──────────────────────────────────────────────────────

class _SpecData:
    """
    Parsed Spec (inner class) data for a Blueprint.

    This replaces the DRF-style ``Meta`` class — we call it ``Spec``
    to avoid collision with the Model's ``Meta``.
    """

    __slots__ = (
        "model",
        "fields",
        "exclude",
        "read_only_fields",
        "write_only_fields",
        "extra_facets",
        "projections",
        "default_projection",
        "depth",
        "validators",
    )

    def __init__(self, spec_cls: type | None = None):
        if spec_cls is None:
            self.model = None
            self.fields = None
            self.exclude = None
            self.read_only_fields = ()
            self.write_only_fields = ()
            self.extra_facets = {}
            self.projections = None
            self.default_projection = None
            self.depth = 3
            self.validators = []
            return

        self.model = getattr(spec_cls, "model", None)
        self.fields = getattr(spec_cls, "fields", None)
        self.exclude = getattr(spec_cls, "exclude", None)
        self.read_only_fields = tuple(getattr(spec_cls, "read_only_fields", ()))
        self.write_only_fields = tuple(getattr(spec_cls, "write_only_fields", ()))
        self.extra_facets = dict(getattr(spec_cls, "extra_facets", {}))
        self.projections = getattr(spec_cls, "projections", None)
        self.default_projection = getattr(spec_cls, "default_projection", None)
        self.depth = getattr(spec_cls, "depth", 3)
        self.validators = list(getattr(spec_cls, "validators", []))


# ── Metaclass ────────────────────────────────────────────────────────────

class BlueprintMeta(type):
    """
    Metaclass for Blueprint classes.

    Responsibilities:
        1. Collect declared Facets from namespace + parent classes
        2. Parse the Spec inner class
        3. Auto-derive Facets from Model fields (if Spec.model is set)
        4. Build the ProjectionRegistry
        5. Set up seal/async_seal method discovery
        6. Support ``Blueprint["projection"]`` subscript syntax
    """

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs,
    ) -> BlueprintMeta:
        # Collect declared facets from namespace
        declared_facets: Dict[str, Facet] = {}
        for key, value in list(namespace.items()):
            if isinstance(value, Facet):
                declared_facets[key] = value

        # Inherit facets from parent Blueprints
        parent_facets: Dict[str, Facet] = {}
        for base in bases:
            if hasattr(base, "_declared_facets"):
                for fname, facet in base._declared_facets.items():
                    if fname not in declared_facets:
                        parent_facets[fname] = facet.clone()

        # Parse Spec inner class
        spec_cls = namespace.pop("Spec", None)

        # Also check bases for Spec
        if spec_cls is None:
            for base in bases:
                if hasattr(base, "_spec") and base._spec is not None:
                    spec_cls = type("Spec", (), {
                        attr: getattr(base._spec, attr)
                        for attr in _SpecData.__slots__
                        if hasattr(base._spec, attr)
                    })
                    break

        spec = _SpecData(spec_cls)

        # Build the class
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        cls._spec = spec
        cls._declared_facets = declared_facets
        cls._parent_facets = parent_facets
        cls._all_facets: Dict[str, Facet] = {}

        # If this is the base Blueprint class itself, skip model derivation
        if spec.model is None and not declared_facets:
            return cls

        # Auto-derive facets from model
        model_facets: Dict[str, Facet] = {}
        if spec.model is not None:
            model_facets = mcs._derive_model_facets(spec)

        # Merge: parent < model < declared (declared wins)
        all_facets = {}
        all_facets.update(parent_facets)
        all_facets.update(model_facets)
        all_facets.update(declared_facets)

        # Add extra facets from Spec
        for fname, facet in spec.extra_facets.items():
            if fname not in all_facets:
                all_facets[fname] = facet

        # Apply read_only/write_only overrides from Spec
        for fname in spec.read_only_fields:
            if fname in all_facets:
                all_facets[fname].read_only = True
        for fname in spec.write_only_fields:
            if fname in all_facets:
                all_facets[fname].write_only = True

        # Sort by creation order
        cls._all_facets = dict(
            sorted(all_facets.items(), key=lambda item: item[1]._order)
        )

        # Build projection registry
        cls._projections = ProjectionRegistry()
        write_only_names = {
            fname for fname, f in cls._all_facets.items() if f.write_only
        }
        cls._projections.configure(
            projections=spec.projections,
            default=spec.default_projection,
            all_facet_names=set(cls._all_facets.keys()),
            write_only_names=write_only_names,
        )

        # Discover seal methods
        cls._seal_methods: List[str] = []
        cls._async_seal_methods: List[str] = []
        for attr_name in dir(cls):
            if attr_name.startswith("seal_") and not attr_name.startswith("__"):
                method = getattr(cls, attr_name, None)
                if callable(method):
                    cls._seal_methods.append(attr_name)
            elif attr_name.startswith("async_seal_") and not attr_name.startswith("__"):
                method = getattr(cls, attr_name, None)
                if callable(method):
                    cls._async_seal_methods.append(attr_name)

        return cls

    @staticmethod
    def _derive_model_facets(spec: _SpecData) -> Dict[str, Facet]:
        """Derive Facets from Model._fields."""
        model = spec.model
        facets: Dict[str, Facet] = {}

        # Get model fields
        model_fields = getattr(model, "_fields", {})
        if not model_fields:
            # Fallback: scan class for Field instances
            try:
                from ..models.fields_module import Field
                for attr_name in dir(model):
                    val = getattr(model, attr_name, None)
                    if isinstance(val, Field):
                        model_fields[attr_name] = val
            except ImportError:
                pass

        # Determine which fields to include
        if spec.fields == "__all__":
            include = set(model_fields.keys())
        elif spec.fields is not None:
            include = set(spec.fields)
        else:
            include = set(model_fields.keys())

        if spec.exclude:
            include -= set(spec.exclude)

        # Derive facets
        for fname in include:
            mf = model_fields.get(fname)
            if mf is None:
                continue

            # Check if it's a relation field
            if hasattr(mf, "to"):
                # ForeignKey / OneToOneField / ManyToManyField
                facets[fname] = _derive_relation_facet(mf, fname, spec)
            else:
                facets[fname] = derive_facet(mf)

        return facets

    def __getitem__(cls, projection: str) -> _ProjectedRef:
        """
        Enable ``Blueprint["projection_name"]`` syntax.

        Returns a _ProjectedRef that can be passed to Lens or used
        as a response_blueprint in route decorators.
        """
        return _ProjectedRef(cls, projection)

    def __repr__(cls) -> str:
        model_name = cls._spec.model.__name__ if cls._spec and cls._spec.model else "None"
        return f"<Blueprint '{cls.__name__}' model={model_name}>"


def _derive_relation_facet(model_field: Any, name: str, spec: _SpecData) -> Facet:
    """
    Derive a Lens or IntFacet for a relation field.

    - ForeignKey → IntFacet (PK reference) by default
    - If the FK field name matches a declared Lens, that takes precedence
    """
    from ..models.fields_module import ManyToManyField, ForeignKey, OneToOneField

    is_many = isinstance(model_field, ManyToManyField)

    # Default: expose as PK reference (IntFacet for FK ID)
    kwargs: Dict[str, Any] = {}
    if getattr(model_field, "null", False):
        kwargs["allow_null"] = True
    if is_many:
        # M2M → list of PKs
        return Facet(read_only=True, **kwargs)

    # FK/OneToOne → ID field
    # The actual column is usually `{name}_id`
    facet = Facet(**kwargs)
    facet.source = f"{name}_id" if isinstance(model_field, (ForeignKey, OneToOneField)) else name
    return facet


# ── Blueprint Base Class ─────────────────────────────────────────────────

class Blueprint(metaclass=BlueprintMeta):
    """
    The Blueprint — a contract between a Model and the outside world.

    A Blueprint declares:
        - **Facets**: what data points are visible/writable
        - **Projections**: named subsets of facets
        - **Seals**: validation rules (field, cross-field, async)
        - **Imprints**: how validated data writes back to the model

    Usage::

        class ProductBlueprint(Blueprint):
            class Spec:
                model = Product
                projections = {
                    "summary": ["id", "name", "price"],
                    "detail": "__all__",
                }

        # Outbound: Model → dict
        bp = ProductBlueprint(instance=product)
        data = bp.to_dict()

        # Inbound: dict → validated data
        bp = ProductBlueprint(data={"name": "Widget", "price": 9.99})
        if bp.is_sealed():
            product = await bp.imprint()

    Args:
        instance: Model instance for outbound (mold) operations.
        data: Raw input data for inbound (cast + seal) operations.
        many: If True, expect a list of instances/data.
        partial: If True, don't require all required fields (PATCH semantics).
        projection: Named projection to use.
        context: Extra context dict (request, container, etc.).
    """

    _spec: _SpecData
    _all_facets: Dict[str, Facet]
    _projections: ProjectionRegistry
    _seal_methods: List[str]
    _async_seal_methods: List[str]

    def __init__(
        self,
        instance: Any = None,
        *,
        data: Any = UNSET,
        many: bool = False,
        partial: bool = False,
        projection: str | None = None,
        context: Dict[str, Any] | None = None,
    ):
        self.instance = instance
        self._input_data = data
        self.many = many
        self.partial = partial
        self._projection_name = projection
        self.context: Dict[str, Any] = context or {}

        # State
        self._validated_data: Dict[str, Any] | None = None
        self._errors: Dict[str, List[str]] = {}
        self._is_sealed: bool | None = None  # None = not yet validated

        # Bind facets to this instance
        self._bound_facets: Dict[str, Facet] = {}
        for fname, facet in self._all_facets.items():
            bound = facet.clone()
            bound.bind(fname, self)
            self._bound_facets[fname] = bound

    # ── Outbound: Mold ───────────────────────────────────────────────

    @property
    def data(self) -> Dict[str, Any] | List[Dict[str, Any]]:
        """
        The output representation — molded from the instance.

        For inbound usage, returns validated_data after sealing.
        """
        if self.instance is not None:
            if self.many:
                return self.to_dict_many(self.instance)
            return self.to_dict()
        if self._validated_data is not None:
            return self._validated_data
        return {}

    def to_dict(
        self,
        instance: Any = None,
        *,
        _depth: int = 0,
        _seen: set | None = None,
    ) -> Dict[str, Any]:
        """
        Mold a model instance into a dict, respecting projections.

        Args:
            instance: Override instance (default: self.instance)
            _depth: Internal depth counter for Lens traversal
            _seen: Internal cycle detection set
        """
        obj = instance or self.instance
        if obj is None:
            return {}

        # Resolve projection
        projection_fields = self._projections.resolve(self._projection_name)

        result: Dict[str, Any] = {}
        for fname, facet in self._bound_facets.items():
            # Skip write-only facets in output
            if facet.write_only:
                continue
            # Apply projection filter
            if projection_fields and fname not in projection_fields:
                continue

            # Extract value from instance
            value = facet.extract(obj)

            # Mold through Lens (with depth/cycle tracking)
            if isinstance(facet, Lens):
                value = facet.mold(value, _depth=_depth, _seen=_seen)
            elif value is not None:
                value = facet.mold(value)
            elif facet.allow_null:
                value = None
            else:
                continue  # Skip None values for non-nullable facets

            result[fname] = value

        return result

    def to_dict_many(
        self,
        instances: Any,
        *,
        _depth: int = 0,
        _seen: set | None = None,
    ) -> List[Dict[str, Any]]:
        """Mold multiple instances."""
        return [
            self.to_dict(instance=obj, _depth=_depth, _seen=_seen)
            for obj in instances
        ]

    # ── Inbound: Cast + Seal ─────────────────────────────────────────

    def is_sealed(self, *, raise_fault: bool = False) -> bool:
        """
        Validate the input data through the full pipeline.

        Pipeline:
            1. Cast: type coercion per facet
            2. Field seals: per-facet validators
            3. Cross-field seals: ``seal_*()`` methods
            4. Object-level validate: ``validate()``

        Args:
            raise_fault: If True, raise BlueprintFault on failure.

        Returns:
            True if data passes all seals.
        """
        if self._is_sealed is not None:
            if raise_fault and not self._is_sealed:
                raise SealFault(
                    message="Blueprint validation failed",
                    errors=self._errors,
                )
            return self._is_sealed

        if self._input_data is UNSET:
            self._errors = {"__all__": ["No input data provided"]}
            self._is_sealed = False
            if raise_fault:
                raise SealFault(message="No input data provided", errors=self._errors)
            return False

        if self.many:
            return self._seal_many(raise_fault=raise_fault)

        self._errors = {}
        validated: Dict[str, Any] = {}

        data = self._input_data if isinstance(self._input_data, dict) else {}

        # Phase 1 + 2: Cast + Field Seals
        for fname, facet in self._bound_facets.items():
            if isinstance(facet, (Computed, Constant)):
                continue

            # Handle DI-injectable facets (even if read_only)
            if isinstance(facet, Inject):
                resolved = facet.resolve_from_context(self.context)
                if resolved is not UNSET:
                    validated[fname] = resolved
                continue

            if facet.read_only:
                continue

            raw = data.get(fname, UNSET)

            # Handle missing values
            if raw is UNSET:
                if self.partial:
                    continue
                if facet.default is not UNSET:
                    default = facet.default() if callable(facet.default) else facet.default
                    validated[fname] = default
                    continue
                if facet.required:
                    self._errors.setdefault(fname, []).append("This field is required")
                    continue
                if facet.allow_null:
                    validated[fname] = None
                    continue
                continue

            # Handle null
            if raw is None:
                if facet.allow_null:
                    validated[fname] = None
                    continue
                self._errors.setdefault(fname, []).append("This field may not be null")
                continue

            # Cast
            try:
                cast_value = facet.cast(raw)
            except CastFault as exc:
                self._errors.setdefault(fname, []).append(str(exc))
                continue
            except (ValueError, TypeError) as exc:
                self._errors.setdefault(fname, []).append(str(exc))
                continue

            # Seal (field-level validation)
            try:
                sealed_value = facet.seal(cast_value)
            except CastFault as exc:
                self._errors.setdefault(fname, []).append(str(exc))
                continue
            except (ValueError, TypeError) as exc:
                self._errors.setdefault(fname, []).append(str(exc))
                continue

            validated[fname] = sealed_value

        if self._errors:
            self._is_sealed = False
            if raise_fault:
                raise SealFault(message="Blueprint validation failed", errors=self._errors)
            return False

        # Phase 3: Cross-field seals (seal_* methods)
        for method_name in self._seal_methods:
            method = getattr(self, method_name, None)
            if method is not None:
                try:
                    method(validated)
                except CastFault as exc:
                    # Extract field from the fault
                    self._errors.setdefault(exc.field, []).append(str(exc))
                except (ValueError, TypeError) as exc:
                    self._errors.setdefault("__all__", []).append(str(exc))

        if self._errors:
            self._is_sealed = False
            if raise_fault:
                raise SealFault(message="Blueprint validation failed", errors=self._errors)
            return False

        # Phase 4: Object-level validate
        try:
            validated = self.validate(validated)
        except CastFault as exc:
            self._errors.setdefault(exc.field, []).append(str(exc))
        except SealFault as exc:
            if exc.field_errors:
                for field, msgs in exc.field_errors.items():
                    self._errors.setdefault(field, []).extend(msgs)
            else:
                self._errors.setdefault("__all__", []).append(str(exc))
        except (ValueError, TypeError) as exc:
            self._errors.setdefault("__all__", []).append(str(exc))

        if self._errors:
            self._is_sealed = False
            if raise_fault:
                raise SealFault(message="Blueprint validation failed", errors=self._errors)
            return False

        self._validated_data = validated
        self._is_sealed = True
        return True

    async def is_sealed_async(self, *, raise_fault: bool = False) -> bool:
        """
        Async variant of is_sealed — also runs async_seal_* methods.

        Pipeline:
            1-4. Same as is_sealed()
            5. Async seals: ``async_seal_*()`` methods
        """
        # Run sync pipeline first
        if not self.is_sealed(raise_fault=False):
            if raise_fault:
                raise SealFault(message="Blueprint validation failed", errors=self._errors)
            return False

        # Phase 5: Async seals
        for method_name in self._async_seal_methods:
            method = getattr(self, method_name, None)
            if method is not None:
                try:
                    await method(self._validated_data)
                except CastFault as exc:
                    self._errors.setdefault(exc.field, []).append(str(exc))
                except (ValueError, TypeError) as exc:
                    self._errors.setdefault("__all__", []).append(str(exc))

        if self._errors:
            self._is_sealed = False
            self._validated_data = None
            if raise_fault:
                raise SealFault(message="Blueprint validation failed", errors=self._errors)
            return False

        return True

    def _seal_many(self, *, raise_fault: bool) -> bool:
        """Validate a list of input items."""
        if not isinstance(self._input_data, (list, tuple)):
            self._errors = {"__all__": ["Expected a list"]}
            self._is_sealed = False
            if raise_fault:
                raise SealFault(message="Expected a list", errors=self._errors)
            return False

        all_validated = []
        all_errors = {}
        for i, item in enumerate(self._input_data):
            child = self.__class__(
                data=item,
                partial=self.partial,
                projection=self._projection_name,
                context=self.context,
            )
            if child.is_sealed():
                all_validated.append(child.validated_data)
            else:
                all_errors[str(i)] = child.errors

        if all_errors:
            self._errors = all_errors
            self._is_sealed = False
            if raise_fault:
                raise SealFault(message="List validation failed", errors=self._errors)
            return False

        self._validated_data = all_validated
        self._is_sealed = True
        return True

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Object-level validation hook.

        Override this to add cross-field logic. Return the (possibly
        modified) data dict, or raise an exception.

        This is the final gate before data is considered sealed.
        """
        return data

    def reject(self, field: str, message: str) -> None:
        """
        Convenience method for seal methods to register a field error.

        Usage in seal_* methods::

            def seal_date_range(self, data):
                if data["end_date"] < data["start_date"]:
                    self.reject("end_date", "Must be after start date")
        """
        raise CastFault(field, message)

    @property
    def validated_data(self) -> Dict[str, Any] | List[Dict[str, Any]] | None:
        """The validated data — only available after successful sealing."""
        if self._is_sealed is None:
            self.is_sealed()
        return self._validated_data

    @property
    def errors(self) -> Dict[str, List[str]]:
        """Validation errors — available after sealing attempt."""
        if self._is_sealed is None:
            self.is_sealed()
        return self._errors

    # ── Write: Imprint ───────────────────────────────────────────────

    async def imprint(
        self,
        instance: Any = None,
        *,
        partial: bool | None = None,
    ) -> Any:
        """
        Write validated data back to a model instance.

        - If ``instance`` is None: creates a new model instance
        - If ``instance`` is provided: updates the existing instance
        - If ``partial`` is True: only update provided fields (PATCH)

        Returns the saved model instance.

        Raises:
            ImprintFault: If sealing hasn't been done or failed.
        """
        if self._validated_data is None:
            raise ImprintFault(
                message="Cannot imprint — data has not been sealed. "
                        "Call is_sealed() first.",
            )

        is_partial = partial if partial is not None else self.partial
        target = instance or self.instance

        if self.many:
            return await self._imprint_many(target)

        if target is not None:
            return await self._imprint_update(target, is_partial)
        return await self._imprint_create()

    async def _imprint_create(self) -> Any:
        """Create a new model instance from validated data."""
        model_cls = self._spec.model
        if model_cls is None:
            raise ImprintFault(message="Cannot imprint without a model class in Spec")

        # Filter to only model-writable fields
        create_data = self._filter_imprint_data(self._validated_data)

        try:
            instance = model_cls(**create_data)
            await instance.save()
            return instance
        except Exception as exc:
            raise ImprintFault(
                message=f"Failed to create {model_cls.__name__}: {exc}",
                metadata={"model": model_cls.__name__, "error": str(exc)},
            ) from exc

    async def _imprint_update(self, instance: Any, partial: bool) -> Any:
        """Update an existing model instance."""
        update_data = self._filter_imprint_data(self._validated_data)
        update_fields = []

        for attr, value in update_data.items():
            setattr(instance, attr, value)
            update_fields.append(attr)

        try:
            if update_fields:
                await instance.save(update_fields=update_fields)
            return instance
        except Exception as exc:
            model_name = type(instance).__name__
            raise ImprintFault(
                message=f"Failed to update {model_name}: {exc}",
                metadata={"model": model_name, "error": str(exc)},
            ) from exc

    async def _imprint_many(self, instances: Any = None) -> List[Any]:
        """Create or update multiple instances."""
        results = []
        for i, item_data in enumerate(self._validated_data):
            child = self.__class__(
                instance=instances[i] if instances and i < len(instances) else None,
                data=item_data,
                partial=self.partial,
                context=self.context,
            )
            child._validated_data = item_data
            child._is_sealed = True
            result = await child.imprint()
            results.append(result)
        return results

    def _filter_imprint_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter validated data to only include model-writable attributes.

        Removes computed facets, constants, and fields not on the model.
        """
        if self._spec.model is None:
            return dict(data)

        model_fields = getattr(self._spec.model, "_fields", {})
        model_attrs = set(model_fields.keys())

        # Also include FK _id columns
        for fname, mf in model_fields.items():
            if hasattr(mf, "to"):
                model_attrs.add(f"{fname}_id")

        result = {}
        for key, value in data.items():
            # Check if the facet is writable
            facet = self._bound_facets.get(key)
            if facet is not None and isinstance(facet, (Computed, Constant, Inject)):
                continue
            # Check if it maps to a model attribute
            source = facet.source if facet else key
            if source in model_attrs or key in model_attrs:
                result[source] = value
            else:
                # Allow through if no model (pure Blueprint)
                result[key] = value

        return result

    # ── Schema ───────────────────────────────────────────────────────

    @classmethod
    def to_schema(
        cls,
        *,
        projection: str | None = None,
        mode: str = "output",
    ) -> Dict[str, Any]:
        """
        Generate JSON Schema for this Blueprint.

        Args:
            projection: Named projection (None = default)
            mode: "output" (mold schema) or "input" (cast schema)

        Returns:
            JSON Schema dict
        """
        projection_fields = cls._projections.resolve(projection)

        properties: Dict[str, Any] = {}
        required: List[str] = []

        for fname, facet in cls._all_facets.items():
            # Filter by mode
            if mode == "output" and facet.write_only:
                continue
            if mode == "input" and facet.read_only:
                continue

            # Apply projection
            if projection_fields and fname not in projection_fields:
                continue

            properties[fname] = facet.to_schema()

            if mode == "input" and facet.required and not facet.read_only:
                required.append(fname)

        schema: Dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required

        title = cls.__name__
        if projection:
            title = f"{title}_{projection}"
        schema["title"] = title

        return schema

    # ── Utilities ────────────────────────────────────────────────────

    @classmethod
    def facet_names(cls, *, projection: str | None = None) -> List[str]:
        """List facet names, optionally filtered by projection."""
        if projection:
            return sorted(cls._projections.resolve(projection))
        return list(cls._all_facets.keys())

    @classmethod
    def get_facet(cls, name: str) -> Facet | None:
        """Get a facet by name."""
        return cls._all_facets.get(name)

    def __repr__(self) -> str:
        model_name = self._spec.model.__name__ if self._spec.model else "None"
        state = "sealed" if self._is_sealed else ("failed" if self._is_sealed is False else "pending")
        return f"<{type(self).__name__} model={model_name} state={state}>"
