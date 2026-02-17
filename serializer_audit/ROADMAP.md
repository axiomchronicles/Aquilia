# Serializer Optimization Roadmap

> Prioritized roadmap for Aquilia serializer performance improvements.
> Items marked ✅ are implemented in this PR; items marked 🔮 are future work.

---

## Phase 1: Core Hot-Path Optimizations (This PR) ✅

### HP-1 ✅ — Replace `copy.deepcopy()` with shallow copy
- **Impact**: 4× faster serializer instantiation
- **Risk**: Low — validators list and error_messages dict are shallow-copied independently
- **Benchmark**: 17.2 µs → 4.3 µs (small, 4 fields)

### HP-2 ✅ — Replace `OrderedDict` with plain `dict`
- **Impact**: Eliminates OrderedDict overhead in metaclass, __init__, to_representation
- **Risk**: None — Python 3.7+ guarantees dict insertion order
- **Benchmark**: Folded into HP-1 numbers

### HP-3 ✅ — Pre-split source paths at `bind()` time
- **Impact**: Eliminates `source.split('.')` on every `get_attribute()` call
- **Risk**: None — source is immutable after bind
- **Benchmark**: simple 291 ns vs dotted 500 ns (1.7× difference)

### HP-4 ✅ — Cache `validate_*` method references
- **Impact**: Eliminates `getattr(self, f"validate_{field_name}", None)` per field per request
- **Risk**: None — class methods don't change between instances
- **Benchmark**: Folded into validation numbers

### HP-5 ✅ — Simple source fast path in `get_attribute()`
- **Impact**: Direct `getattr()`/`dict.get()` for non-dotted sources (95%+ of fields)
- **Risk**: None — falls through to full traversal for dotted/star sources

### HP-6 ✅ — `source="*"` priority check in `to_representation()`
- **Impact**: Fixes SerializerMethodField correctness after HP-5
- **Risk**: Bug found and fixed during testing

---

## Phase 2: New Capabilities (This PR) ✅

### NC-1 ✅ — StreamingSerializer
- Generator-based streaming for large JSON arrays
- Chunk-based buffering with configurable chunk_size
- Both sync (`stream()`) and async (`stream_async()`) interfaces
- Uses BufferPool for zero-alloc buffer reuse

### NC-2 ✅ — BufferPool
- Thread-local reusable bytearray pool
- `acquire()`/`release()` pattern
- Configurable pool size (default 16)
- 250 ns per acquire/release cycle

### NC-3 ✅ — SerializerConfig
- Global JSON backend configuration (`"orjson"`, `"ujson"`, `"stdlib"`, `"auto"`)
- `get_json_encoder()` / `get_json_decoder()` with caching
- `reset()` for testing/reconfiguration

---

## Phase 3: Future Optimizations 🔮

### FP-1 🔮 — Compiled representation plans (Priority: High)
- Pre-compile `to_representation()` into a specialized function per serializer class
- Use `_FieldPlanEntry` tuples (already defined) to build an unrolled loop
- Expected: 2–3× additional speedup for to_representation
- Complexity: Medium

### FP-2 🔮 — `__slots__` on Serializer instances (Priority: Medium)
- Add `__slots__` to `Serializer` and `SerializerField` base classes
- Reduces per-instance memory by ~40%
- Complexity: High (requires audit of all dynamic attribute assignments)

### FP-3 🔮 — JIT field type dispatch (Priority: Medium)
- Replace virtual `to_representation()` dispatch with type-based lookup table
- For fields with trivial transforms (CharField → identity, IntegerField → int())
- Expected: 30–50% speedup for simple fields
- Complexity: Medium

### FP-4 🔮 — Lazy field binding (Priority: Low)
- Only bind fields that are actually accessed in the current request
- Useful for serializers with many optional/conditional fields
- Expected: Proportional to unused field count
- Complexity: Low

### FP-5 🔮 — Response-level serializer caching (Priority: Low)
- Cache serialized output for identical instances (content-addressed)
- Useful for read-heavy endpoints with stable data
- Expected: Near-zero cost for cache hits
- Complexity: High (cache invalidation)

### FP-6 🔮 — Cython/mypyc compilation (Priority: Low)
- Compile `fields.py` and `base.py` hot paths with mypyc
- Expected: 5–10× for numeric operations, 2–3× for attribute access
- Complexity: High (build system, CI, platform support)

---

## Metrics Summary

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Instantiation (small) | 17.2 µs | 4.3 µs | **4.0×** |
| Instantiation (medium) | 42.8 µs | 10.8 µs | **4.0×** |
| Instantiation (large) | 86.3 µs | 22.0 µs | **3.9×** |
| to_repr (small) | — | 1.3 µs | baseline |
| to_repr (medium) | — | 4.0 µs | baseline |
| to_repr (large) | — | 7.4 µs | baseline |
| Validation (small) | — | 5.8 µs | baseline |
| List 1000 items | — | 1.2 ms | baseline |
| Streaming 1000 items | — | 1.4 ms | N/A (new) |
| Buffer pool cycle | — | 250 ns | N/A (new) |
| get_attribute (simple) | — | 291 ns | fast path |
| get_attribute (dotted) | — | 500 ns | 1.7× vs simple |
| Allocs per small ser. | — | 816 bytes | baseline |

> "Before" values for to_repr/validation are not available as standalone benchmarks
> were not previously instrumented. The deepcopy → shallow copy comparison provides
> the most meaningful before/after data.
