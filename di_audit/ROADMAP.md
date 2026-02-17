# Optimization Roadmap — DI + Models/DB

## Phase B Summary (Current Session)

### Completed
1. **DI Audit** — Full 12-file, 3500-LOC analysis. No dead code. No critical wiring issues.
2. **DI Optimizations** — 4 targeted changes in `core.py`:
   - Module-level `_type_key_cache` for type→string mapping
   - `_CACHEABLE_SCOPES` frozenset constant
   - Inlined `_token_to_key` in `resolve_async` hot path
   - `__slots__` on `ResolveCtx`
3. **Models Audit** — Full analysis of metaclass, base, query, manager, fields, signals, SQL builders
4. **Models Optimizations** — 10 changes across 4 files:
   - `_non_m2m_fields` tuple and `_col_to_attr` dict on metaclass
   - `__init__`, `from_row`, `create`, `bulk_create`, `save`, `generate_create_table_sql` all optimized
   - `_cached_lookup_registry` and `_EXPR_OP_MAP` in query.py
5. **DB Audit** — engine.py, backends analyzed. No issues found.
6. **Benchmarks** — `bench_di.py` and `bench_models.py` created
7. **Test validation** — 3527 tests, 0 regressions

### Measured Results

#### DI Subsystem
| Metric | Before | After | Factor |
|--------|--------|-------|--------|
| resolve_async (cached, type) | 0.25µs | 0.17µs | 1.47× |
| resolve_async (cached, str) | 0.17µs | 0.12µs | 1.42× |
| resolve_async (cold, no deps) | 1.12µs | 0.92µs | 1.22× |
| resolve_async (cold, 1 dep) | 2.17µs | 1.83µs | 1.19× |
| Full lifecycle (1 resolve) | 0.67µs | 0.54µs | 1.24× |
| Full lifecycle (3 resolves) | 1.62µs | 1.21µs | 1.34× |

#### Models Subsystem (Post-Optimization Absolute Numbers)
| Metric | Value |
|--------|-------|
| Model.__init__ (2 fields) | 1.43µs |
| Model.__init__ (6 fields) | 0.99µs |
| from_row (8 cols) | 0.88µs |
| from_row (5 cols) | 0.60µs |
| Q().filter(1 clause) | 1.13µs |
| Q().filter().order().limit() | 2.95µs |
| generate_create_table_sql (8 fields) | 3.16µs |

---

## Future Optimization Opportunities (Phase C)

### Priority 1: High Impact, Low Risk

#### 1.1 Prepared Statement Caching (PostgreSQL)
- **What**: Cache `asyncpg.prepare()` calls for repeated queries
- **Where**: `aquilia/db/backends/postgres.py`
- **Impact**: 2-5× for repeated SELECT/INSERT patterns
- **Risk**: Low — asyncpg natively supports this

#### 1.2 Batch Insert Optimization
- **What**: `bulk_create()` currently does N individual INSERTs. Change to multi-row INSERT.
- **Where**: `aquilia/models/base.py` → `bulk_create()`
- **Impact**: 10-50× for large batch inserts (single round-trip vs N)
- **Risk**: Medium — need to handle `lastrowid` for each row

#### 1.3 Connection Pool Warmup
- **What**: Pre-create connection pool on startup instead of lazy init
- **Where**: `aquilia/db/engine.py` → `on_startup()`
- **Impact**: Eliminates first-request latency spike
- **Risk**: Low

### Priority 2: Medium Impact

#### 2.1 Query Result Caching
- **What**: Optional per-request query cache for identical SELECT queries
- **Where**: New `aquilia/db/query_cache.py`
- **Impact**: Eliminates duplicate DB round-trips in request lifecycle
- **Risk**: Medium — cache invalidation on writes

#### 2.2 Model `__init__` with `__slots__`
- **What**: Add `__slots__` to Model subclasses via metaclass
- **Where**: `aquilia/models/metaclass.py`
- **Impact**: ~30% memory reduction, slightly faster attribute access
- **Risk**: Medium — breaks dynamic attribute assignment patterns

#### 2.3 Lazy Import Optimization in Query Builder
- **What**: `_build_filter_clause` imports `Expression`, `Combinable` at function level
- **Where**: `aquilia/models/query.py`
- **Impact**: Small — eliminate import overhead per filter call
- **Risk**: Low — move to module level

### Priority 3: Architectural Improvements

#### 3.1 Compiled Query Plans
- **What**: Pre-compile common query patterns (CRUD) into SQL templates at model registration
- **Where**: New `aquilia/models/compiled.py`
- **Impact**: Eliminate SQL string building for common operations
- **Risk**: High — significant refactor

#### 3.2 DI Resolution Plans
- **What**: `_resolve_plans` field in Container is allocated but unused. Implement pre-computed dependency resolution order.
- **Where**: `aquilia/di/core.py`
- **Impact**: Eliminate recursive `resolve_async` for deep dependency chains
- **Risk**: Medium

#### 3.3 Zero-Copy Row Mapping
- **What**: Map DB rows directly to model instances without intermediate dict
- **Where**: `aquilia/models/base.py` → `from_row()`
- **Impact**: Eliminate dict allocation for each row
- **Risk**: Medium — backend-specific (asyncpg Record vs aiosqlite Row)

---

## Files Modified in This Session

| File | Changes |
|------|---------|
| `aquilia/di/core.py` | `_type_key_cache`, `_CACHEABLE_SCOPES`, inlined resolve_async, ResolveCtx __slots__ |
| `aquilia/models/metaclass.py` | `_non_m2m_fields` tuple, `_col_to_attr` dict |
| `aquilia/models/base.py` | __init__, from_row, create, bulk_create, save, generate_create_table_sql |
| `aquilia/models/query.py` | `_cached_lookup_registry`, `_EXPR_OP_MAP` |

## New Files Created

| File | Purpose |
|------|---------|
| `benchmarks/bench_di.py` | DI subsystem microbenchmark |
| `benchmarks/bench_models.py` | Models subsystem microbenchmark |
| `di_audit/audit_di.py` | Automated DI dead code/wiring scanner |
| `di_audit/AUDIT_REPORT.md` | Full audit findings |
| `di_audit/REGRESSION_CHECKLIST.md` | Test & performance regression checklist |
| `di_audit/ROADMAP.md` | This file |
