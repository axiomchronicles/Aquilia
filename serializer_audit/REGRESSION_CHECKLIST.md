# Serializer Optimization — Regression Checklist & Rollback Plan

## Pre-Merge Checklist

### ✅ Correctness

- [ ] All 243 existing serializer tests pass (`tests/test_serializers.py`)
- [ ] All 60 optimization tests pass (`tests/test_serializer_optimizations.py`)
- [ ] All 81 export tests pass (`tests/test_exports.py`)
- [ ] All 22 mail+serializer DI tests pass (`tests/test_mail_serializer_di.py`)
- [ ] SerializerMethodField (`source="*"`) works correctly
- [ ] Nested serializers produce correct output
- [ ] ListSerializer produces correct output
- [ ] Partial validation works
- [ ] DI defaults (`CurrentUserDefault`, `InjectDefault`) resolve correctly
- [ ] write_only / read_only field exclusion works
- [ ] Validators run in correct order
- [ ] Error messages are independent between serializer instances

### ✅ Performance

- [ ] Instantiation ≥ 3.5× faster than deepcopy baseline
- [ ] No memory regression (allocation per serialization ≤ 1KB for small serializers)
- [ ] BufferPool acquire/release ≤ 500 ns
- [ ] StreamingSerializer produces valid JSON for 1000+ items

### ✅ API Compatibility

- [ ] `Serializer.data` returns `dict` (was `OrderedDict`, but `dict` is a superset)
- [ ] `Serializer.errors` structure unchanged
- [ ] `Serializer.is_valid()` signature unchanged
- [ ] `Serializer.validated_data` structure unchanged
- [ ] `ListSerializer.data` returns `list[dict]`
- [ ] `Serializer.many()` class method works
- [ ] All field types serialize/deserialize identically
- [ ] `_declared_fields` class attribute still accessible
- [ ] Serializer inheritance chains work

### ✅ New Features

- [ ] `StreamingSerializer` importable from `aquilia.serializers`
- [ ] `BufferPool` importable from `aquilia.serializers`
- [ ] `SerializerConfig` importable from `aquilia.serializers`
- [ ] `get_buffer_pool` importable from `aquilia.serializers`

---

## Breaking Change Assessment

### ⚠️ Potential Breaking Change: `dict` instead of `OrderedDict`

**What changed**: `Serializer.data` and `to_representation()` now return a plain `dict` instead of `collections.OrderedDict`.

**Who is affected**: Code that explicitly checks `isinstance(data, OrderedDict)` or uses `OrderedDict`-specific methods (`.move_to_end()`, `.popitem(last=True)`).

**Mitigation**: Python 3.7+ dicts preserve insertion order. The `dict` type is a superclass of `OrderedDict`, so `isinstance(data, dict)` still returns `True`. No code in the Aquilia codebase uses `OrderedDict`-specific methods on serializer output.

**Risk**: **Very Low** — This is consistent with Django REST Framework's own migration path.

### ✅ Non-Breaking Changes

- Shallow copy instead of deepcopy: Field instances are still independent copies
- Pre-split sources: Internal optimization, no API change
- Cached validate methods: Same behavior, just faster lookup
- New classes (StreamingSerializer, etc.): Additive, no existing code affected

---

## Rollback Plan

### Quick Rollback (< 5 minutes)

```bash
# Revert all serializer changes
git revert <commit-hash>
```

### Surgical Rollback (per optimization)

Each optimization is independently revertable:

#### 1. Revert shallow copy → deepcopy

In `aquilia/serializers/base.py`, `Serializer.__init__`:
```python
# Change this:
import copy
field_copy = copy.copy(field)
field_copy.validators = list(field.validators)
field_copy.error_messages = dict(field.error_messages)

# Back to:
import copy
field_copy = copy.deepcopy(field)
```

#### 2. Revert dict → OrderedDict

In `aquilia/serializers/base.py`:
```python
# Re-add:
from collections import OrderedDict

# In SerializerMeta, Serializer.__init__, to_representation:
# Replace dict() with OrderedDict()
```

#### 3. Revert pre-split sources

In `aquilia/serializers/fields.py`, `bind()`:
```python
# Remove:
self._source_parts = tuple(self.source.split("."))
self._simple_source = len(self._source_parts) == 1

# In get_attribute(), remove the fast path and use original split() logic
```

#### 4. Revert cached validate methods

In `aquilia/serializers/base.py`, `Serializer.__init__` and `run_validation()`:
```python
# Remove _validate_methods cache
# In run_validation, revert to:
validator = getattr(self, f"validate_{field_name}", None)
```

#### 5. Remove new features

Simply remove imports from `aquilia/serializers/__init__.py`:
- `StreamingSerializer`
- `BufferPool`
- `SerializerConfig`
- `get_buffer_pool`

The classes in `base.py` can remain unused without any side effects.

---

## Monitoring After Deploy

### Key Metrics to Watch

1. **Request latency P50/P95/P99** — should decrease by 5–15% for serializer-heavy endpoints
2. **Memory usage** — should decrease or stay flat (fewer allocations)
3. **Error rate** — should be unchanged (any increase = immediate rollback)
4. **Serializer-specific errors** — `ValidationFault`, `SerializationFault` rates

### Smoke Test Endpoints

After deploy, manually verify these patterns:

```bash
# Simple serializer (request + response)
curl -X POST /api/v1/users -d '{"name":"test","email":"test@test.com"}'

# List endpoint (ListSerializer)
curl /api/v1/users?limit=100

# Nested serializer
curl /api/v1/users/1?include=profile

# Validation errors
curl -X POST /api/v1/users -d '{"name":"","email":"invalid"}'
```

### Automated Regression Test

```bash
# Run full test suite
python -m pytest tests/test_serializers.py tests/test_serializer_optimizations.py -v

# Run benchmarks and compare
./serializer_bench/run_bench_local.sh
```
