# Endpoints Using Serialization

> Auto-generated mapping of all code paths in Aquilia that invoke the serializer subsystem.

## Controller Layer

| File | Function/Method | Serializer Usage | Hot Path? |
|------|----------------|------------------|-----------|
| `aquilia/controller/engine.py` | `_apply_request_serializer()` | Instantiates `request_serializer(data=body, context=ctx)`, calls `is_valid(raise_fault=True)` | ✅ Yes — every request with `@route(request_serializer=...)` |
| `aquilia/controller/engine.py` | `_apply_response_serializer()` | Instantiates `response_serializer(instance=result)`, returns `.data` | ✅ Yes — every response with `@route(response_serializer=...)` |
| `aquilia/controller/engine.py` | `_is_serializer_class()` | Type check: `issubclass(obj, Serializer)` | ❌ No — metadata resolution only |
| `aquilia/controller/metadata.py` | `_is_serializer_type()` | Type check for route metadata | ❌ No — startup only |
| `aquilia/controller/decorators.py` | `@route()` | Stores `request_serializer` / `response_serializer` on route metadata | ❌ No — decorator (startup) |

## Response Layer

| File | Function/Method | Serializer Usage | Hot Path? |
|------|----------------|------------------|-----------|
| `aquilia/response.py` | `JSONResponse.json()` | Uses `orjson.dumps` → `ujson.dumps` → `json.dumps` fallback for final encoding | ✅ Yes — every JSON response |

## Dependency Injection

| File | Function/Method | Serializer Usage | Hot Path? |
|------|----------------|------------------|-----------|
| `aquilia/di/providers.py` | Provider resolution | Resolves `CurrentUserDefault`, `CurrentRequestDefault`, `InjectDefault` for hidden/default fields | ✅ Yes — on every serializer with DI defaults |

## Mail Integration

| File | Function/Method | Serializer Usage | Hot Path? |
|------|----------------|------------------|-----------|
| `aquilia/mail/config.py` | `MailConfig` | Uses serializer for mail configuration validation | ❌ No — startup/config only |

## MLOps

| File | Function/Method | Serializer Usage | Hot Path? |
|------|----------------|------------------|-----------|
| `aquilia/mlops/serializers.py` | Various ML serializers | `PredictionInputSerializer`, `PredictionOutputSerializer`, etc. | ⚠️ Medium — per-prediction request |

## Summary

### Critical Hot Paths (optimized in this PR)

1. **Serializer instantiation** — `Serializer.__init__` called per-request for both request and response serializers.
   - **Before**: `copy.deepcopy()` per field → **17.2 µs** (small), **86.3 µs** (large)
   - **After**: `copy.copy()` + shallow validator/error_messages copy → **4.3 µs** (small), **22.0 µs** (large)
   - **Speedup**: 3.9–4.0×

2. **`to_representation()`** — called per-response to serialize model → dict.
   - Pre-split source paths avoid `str.split('.')` per field per request.
   - Simple source fast path: direct `getattr()` / `dict.__getitem__()`.
   - Plain `dict` output instead of `OrderedDict`.

3. **`run_validation()`** — called per-request for request body deserialization.
   - Cached `validate_*` method lookup: resolved once per class, not per instance.

4. **JSON encoding** — `response.py` already optimized with orjson/ujson fallback.
   - New `SerializerConfig` allows explicit backend selection.

### Non-Hot Paths (no optimization needed)

- Route registration (`@route`, `_is_serializer_type`) — startup only
- Mail config validation — startup only
- Controller metadata resolution — startup only
