# Aquilia Blueprint System — Architecture Document

## Vision

Aquilia's **Blueprint** system replaces the traditional "ModelSerializer" concept
with a first-class framework primitive that feels native to Aquilia's async-first,
signal-driven, DI-integrated architecture. A Blueprint is a *contract* between a
Model and the outside world — it declares what the world sees, what it can send,
and how the framework enforces the boundary.

> **Naming philosophy:** A Blueprint defines the *shape* of data that flows in and
> out — just as an architectural blueprint defines how a building interfaces with
> its environment while hiding internal structure.

---

## Core Abstractions

| Aquilia Concept | DRF Equivalent | Why Different |
|---|---|---|
| `Blueprint` | `ModelSerializer` | Declarative contract, not a "serializer" — it *is* the model's public API |
| `Facet` | Serializer field | A facet of the model exposed to the world |
| `Lens` | Nested serializer | A view into a related model — depth-aware, cycle-safe |
| `Projection` | `fields=` / `exclude=` | Named reusable field subsets (like SQL views) |
| `Seal` | Validator | A validation constraint that "seals" data integrity |
| `Imprint` | `create()` / `update()` | A write operation that "imprints" data onto a model |
| `Mold` | `to_representation` | Shapes outgoing data — the output mold |
| `Cast` | `to_internal_value` | Casts incoming data into internal form |

---

## Design Principles

1. **Blueprint-first, not serializer-first:** A Blueprint *declares* the contract.
   Serialization/deserialization are implementation details.

2. **Projections over field lists:** Instead of `fields = ["id", "name"]`, define
   named projections like `summary`, `detail`, `admin` — reusable, composable,
   and selectable at route level.

3. **Facets auto-derive from Model fields:** Zero config for the common case. The
   Blueprint metaclass reads `Model._fields` and generates `Facet` instances with
   correct types, constraints, and defaults — but you can override any facet.

4. **Lenses for relations:** Nested/related data uses `Lens` — a depth-controlled,
   cycle-safe projection into another Blueprint. Circular references are detected
   at class-creation time.

5. **Seals for validation:** Multi-layer: field-level (`Facet.cast()`), cross-field
   (`seal_` methods), object-level (`validate()`), async DB-level (`async_seal_`).

6. **Imprints for writes:** `blueprint.imprint()` creates, `blueprint.imprint(instance)`
   updates. Partial updates use `blueprint.imprint(instance, partial=True)`.

7. **Deep integration:** Blueprints auto-bind in controllers via type annotations,
   produce OpenAPI schemas, integrate with DI, respect model signals, and
   participate in the fault domain system.

---

## File Layout

```
aquilia/blueprints/
    __init__.py          # Public API exports
    core.py              # Blueprint base class + BlueprintMeta metaclass
    facets.py            # Facet field types (auto-derived from model fields)
    lenses.py            # Lens (nested/relation) system
    projections.py       # Named projection system
    seals.py             # Validation pipeline (Seal, AsyncSeal)
    imprints.py          # Write operations (create/update/partial)
    molds.py             # Output shaping hooks
    casts.py             # Input casting hooks
    schema.py            # OpenAPI/JSON Schema generation
    integration.py       # Controller, DI, request/response integration
    exceptions.py        # Blueprint-specific faults
```

---

## API Examples

### Minimal Blueprint (zero config)

```python
from aquilia.blueprints import Blueprint
from myapp.models import Product

class ProductBlueprint(Blueprint):
    class Spec:
        model = Product
```

This auto-generates all facets from `Product._fields`, marks PKs and auto-now
fields as read-only, maps ForeignKeys to `Lens` instances, and creates a
default projection containing all fields.

### Named Projections

```python
class ProductBlueprint(Blueprint):
    class Spec:
        model = Product
        projections = {
            "summary": ["id", "name", "price"],
            "detail": ["id", "name", "description", "price", "category", "created_at"],
            "admin": "__all__",
        }
        default_projection = "detail"
```

Route-level selection:
```python
@GET("/products", response_blueprint=ProductBlueprint["summary"])
async def list_products():
    return await Product.objects.all()

@GET("/products/{id}", response_blueprint=ProductBlueprint["detail"])
async def get_product(id: int):
    return await Product.objects.get(id=id)
```

### Custom Facets (override auto-derived)

```python
from aquilia.blueprints import Blueprint, Facet
from aquilia.blueprints.facets import Computed, WriteOnly, Constant

class UserBlueprint(Blueprint):
    # Override: hide password in output, require on input
    password = Facet.write_only(min_length=8)

    # Computed facet — not stored, derived at output time
    full_name = Computed(lambda user: f"{user.first_name} {user.last_name}")

    # Constant — always present in output
    api_version = Constant("v2")

    class Spec:
        model = User
        projections = {
            "public": ["id", "username", "full_name"],
            "profile": ["id", "username", "email", "full_name", "created_at"],
        }
```

### Lenses (nested relations)

```python
class OrderBlueprint(Blueprint):
    # Lens into UserBlueprint with "public" projection, depth=1
    customer = Lens(UserBlueprint["public"])

    # Lens with explicit depth control
    items = Lens(OrderItemBlueprint, many=True, depth=2)

    class Spec:
        model = Order
```

### Validation Pipeline (Seals)

```python
class RegistrationBlueprint(Blueprint):
    class Spec:
        model = User

    # Field-level: handled by Facet.cast() automatically

    # Cross-field seal (sync)
    def seal_passwords_match(self, data):
        if data.get("password") != data.get("password_confirm"):
            self.reject("password_confirm", "Passwords do not match")

    # Async seal (can hit DB)
    async def async_seal_unique_email(self, data):
        if await User.objects.filter(email=data["email"]).exists():
            self.reject("email", "Email already registered")

    # Object-level validate (final gate)
    def validate(self, data):
        if data.get("age", 0) < 13:
            self.reject("age", "Must be at least 13 years old")
        return data
```

### Imprints (write operations)

```python
# In a controller:
@POST("/users")
async def create_user(blueprint: RegistrationBlueprint):
    # blueprint.data is already validated (auto-injected by controller engine)
    user = await blueprint.imprint()  # Creates new User, respects signals
    return user, 201

@PATCH("/users/{id}")
async def update_user(id: int, blueprint: UserBlueprint):
    user = await User.objects.get(id=id)
    updated = await blueprint.imprint(user, partial=True)  # PATCH semantics
    return updated
```

### DI Integration

```python
from aquilia.blueprints.facets import Inject

class OrderBlueprint(Blueprint):
    # Inject pricing service at validation time
    total = Inject(PricingService, via="calculate_total")

    class Spec:
        model = Order
```

---

## Validation Pipeline Flow

```
Input Data
    │
    ▼
┌─────────────────┐
│  1. Cast Phase   │  Facet.cast() — type coercion per field
│                  │  (str→int, ISO→datetime, etc.)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. Facet Seals  │  Per-field validators (min/max, regex, etc.)
│                  │  From model field constraints + explicit validators
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. Cross-field  │  seal_* methods — cross-field consistency
│     Seals        │  (passwords match, date ranges valid, etc.)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. Async Seals  │  async_seal_* methods — DB/service checks
│                  │  (unique constraints, foreign key exists, etc.)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. validate()   │  Final object-level gate
│                  │  Can transform data before return
└────────┬────────┘
         │
         ▼
    Validated Data
```

---

## Integration Points

### Controller Engine
- Blueprints are auto-detected in handler type annotations (like Serializers today)
- `request_blueprint` and `response_blueprint` decorator kwargs
- Projection selection via `Blueprint["projection_name"]`

### Response Rendering
- `Blueprint.mold(instance)` → dict → `Response.json()`
- `Blueprint.mold_many(queryset)` → streaming-compatible

### Fault Domain
- New `BLUEPRINT` fault domain
- `BlueprintFault`, `CastFault`, `SealFault` hierarchy
- Structured error responses with field→message mapping

### Signals
- `pre_imprint` / `post_imprint` signals
- Blueprint-aware: signals receive the Blueprint instance + validated data

### DI Container
- Blueprints can declare DI dependencies via `Inject` facets
- Container auto-injected via controller context

### OpenAPI Schema
- `Blueprint.to_schema()` generates JSON Schema
- Per-projection schemas
- Supports `$ref` for Lens'd Blueprints

---

## Design Trade-offs vs DRF

| Aspect | DRF | Aquilia Blueprint | Why |
|---|---|---|---|
| Naming | `Serializer` | `Blueprint` | It's a contract, not just serialization |
| Field subsets | `fields = [...]` | Named `projections` | Reusable, route-selectable, composable |
| Nested | `depth=N` or nested serializer | `Lens` with projection | Explicit, cycle-safe, projection-aware |
| Validation | `validate_<field>()` | `seal_*()` / `async_seal_*()` | Separates sync/async, clearer naming |
| Write ops | `create()` / `update()` | `imprint()` | Single method, mode-aware |
| DI | None | First-class `Inject` facets | Framework-native |
| Config | `Meta` inner class | `Spec` inner class | Distinct from model's `Meta` |
| Projection at route | Not built-in | `Blueprint["name"]` subscript | Zero boilerplate |
