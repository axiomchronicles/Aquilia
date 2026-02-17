# Framework Shootout — Benchmark Report

**Aquilia vs Sanic vs FastAPI**

---

## 1. Test Environment

| Parameter | Value |
|-----------|-------|
| **Host OS** | macOS (Apple Silicon) |
| **Docker** | 28.5.1 (desktop-linux) |
| **Container Limits** | `--cpus=2 --memory=512m` per framework |
| **Python** | 3.11-slim (Docker images) |
| **Workers** | 4 per framework (uvicorn / Sanic built-in) |
| **Load Generator** | wrk 4.2.0, 4 threads, 50 concurrent connections |
| **Duration** | 30 seconds per run, 10 second warmup, 3 runs (median reported) |
| **Date** | 2026-02-18 |

### Container Details

| Framework | Container | Port | Memory Usage | CPU (idle) |
|-----------|-----------|------|-------------|------------|
| Aquilia 0.2.0 | framework-shootout-aquilia-1 | 8084 | 200.2 MiB / 512 MiB (39%) | 1.22% |
| Sanic 23.12.x | framework-shootout-sanic-1 | 8085 | 144.4 MiB / 512 MiB (28%) | 1.48% |
| FastAPI 0.110.x | framework-shootout-fastapi-1 | 8083 | 175.0 MiB / 512 MiB (34%) | 1.22% |

---

## 2. Scenarios Tested

| # | Scenario | Endpoint | What It Measures |
|---|----------|----------|-----------------|
| 1 | **Ping** | `GET /ping` | Minimal text response — pure framework overhead |
| 2 | **JSON** | `GET /json` | Small JSON serialization (~200 bytes) |
| 3 | **JSON Large** | `GET /json-large` | Large JSON serialization (~38 KB array of 1000 objects) |
| 4 | **HTML** | `GET /html` | HTML template rendering |
| 5 | **Stream** | `GET /stream` | Chunked streaming response (10 chunks of 1 KB each) |

---

## 3. Per-Scenario Results (Median of 3 Runs)

### 3.1 Ping — `GET /ping`

| Rank | Framework | Req/s | p50 (ms) | p90 (ms) | p99 (ms) | Errors |
|------|-----------|------:|--------:|--------:|--------:|-------:|
| 🥇 | **Sanic** | **23,522** | 1.38 | 22.35 | 41.00 | 0 |
| 🥈 | **FastAPI** | 19,721 | 1.53 | 27.50 | 45.05 | 0 |
| 🥉 | **Aquilia** | 4,543 | 6.43 | 46.38 | 65.79 | 0 |

> Sanic leads by **+19.3%** over FastAPI and **+418%** over Aquilia in raw throughput.

### 3.2 JSON — `GET /json`

| Rank | Framework | Req/s | p50 (ms) | p90 (ms) | p99 (ms) | Errors |
|------|-----------|------:|--------:|--------:|--------:|-------:|
| 🥇 | **Sanic** | **23,404** | 1.35 | 23.33 | 41.12 | 0 |
| 🥈 | **FastAPI** | 17,691 | 1.64 | 29.91 | 47.23 | 0 |
| 🥉 | **Aquilia** | 4,895 | 5.93 | 45.02 | 64.56 | 0 |

> Sanic leads by **+32.3%** over FastAPI. Aquilia at ~1/5 the throughput.

### 3.3 JSON Large — `GET /json-large`

| Rank | Framework | Req/s | p50 (ms) | p90 (ms) | p99 (ms) | Errors |
|------|-----------|------:|--------:|--------:|--------:|-------:|
| 🥇 | **Sanic** | **4,000** | 11.41 | 14.66 | 46.13 | 0 |
| 🥈 | **Aquilia** | 2,747 | 11.14 | 49.38 | 92.17 | 0 |
| 🥉 | **FastAPI** | 480 | 97.61 | 111.50 | 249.30 | 0 |

> **Notable:** Aquilia beats FastAPI handily here (**+472%**). FastAPI's Pydantic serialization overhead shows on large payloads. Sanic's built-in `ujson` dominates.

### 3.4 HTML — `GET /html`

| Rank | Framework | Req/s | p50 (ms) | p90 (ms) | p99 (ms) | Errors |
|------|-----------|------:|--------:|--------:|--------:|-------:|
| 🥇 | **Sanic** | **23,697** | 1.37 | 22.01 | 39.76 | 0 |
| 🥈 | **FastAPI** | 18,763 | 1.62 | 26.45 | 42.21 | 0 |
| 🥉 | **Aquilia** | 4,560 | 6.40 | 46.30 | 66.78 | 0 |

> Similar pattern to ping/json — Sanic's C-level HTTP parser and custom serializer give it an edge.

### 3.5 Stream — `GET /stream`

| Rank | Framework | Req/s | p50 (ms) | p90 (ms) | p99 (ms) | Errors |
|------|-----------|------:|--------:|--------:|--------:|-------:|
| 🥇 | **FastAPI** | **19** | 1,040 | 1,800 | 1,980 | 994 |
| 🥈 | **Sanic** | 19 | 1,450 | 1,920 | 1,980 | 1,014 |
| 🥉 | **Aquilia** | 16 | 1,540 | 1,910 | 1,990 | 987 |

> **Note:** Streaming responses are deliberately slow — each chunk is emitted with `asyncio.sleep(0.1)`, so all frameworks are gated at ~19 req/s. The errors are wrk timeouts due to the inherently slow response. This scenario is not meaningful for throughput comparison — all three are effectively **tied**.

---

## 4. Executive Summary — Winners by Scenario

| Scenario | 🏆 Winner | Req/s | Runner-up | Req/s | Margin |
|----------|----------|------:|-----------|------:|-------:|
| Ping | **Sanic** | 23,522 | FastAPI | 19,721 | +19.3% |
| JSON | **Sanic** | 23,404 | FastAPI | 17,691 | +32.3% |
| JSON Large | **Sanic** | 4,000 | Aquilia | 2,747 | +45.6% |
| HTML | **Sanic** | 23,697 | FastAPI | 18,763 | +26.3% |
| Stream ⚠️ | FastAPI | 19 | Sanic | 19 | +1.3% |

> ⚠️ Stream is I/O-gated (sleep-based); all frameworks effectively tied.

---

## 5. Scorecard

| Framework | Wins | 2nd Place | 3rd Place | Overall |
|-----------|-----:|----------:|----------:|---------|
| **Sanic** | 4 | 1 | 0 | 🥇 **Winner** |
| **FastAPI** | 1 | 3 | 1 | 🥈 Runner-up |
| **Aquilia** | 0 | 1 | 4 | 🥉 |

---

## 6. Resource Efficiency

| Framework | Memory (idle) | Memory % of Limit | PIDs |
|-----------|-------------:|------------------:|-----:|
| **Sanic** | 144.4 MiB | 28% | 29 |
| **FastAPI** | 175.0 MiB | 34% | 29 |
| **Aquilia** | 200.2 MiB | 39% | 26 |

> Sanic is the most memory-efficient, using 28% less memory than Aquilia.

---

## 7. Analysis & Insights

### Why Sanic Dominates

1. **C-level HTTP parsing** — Sanic uses `httptools` (Joyent's http-parser bindings) vs. pure-Python parsing in other frameworks.
2. **Built-in ujson** — Sanic ships with `ujson` by default for JSON serialization, which is significantly faster than Python's `json` module.
3. **Minimal middleware** — Sanic's request pipeline has fewer layers of abstraction.
4. **Mature async runtime** — Battle-tested event loop integration with tuned connection handling.

### FastAPI's Position

- FastAPI performs well on simple endpoints (~18-20k req/s) but drops dramatically on **JSON-large** (480 req/s) due to Pydantic serialization overhead.
- Excellent developer experience (OpenAPI, type hints, dependency injection) comes at a runtime cost.

### Aquilia's Position

- **~4,500-5,000 req/s** on simple endpoints — roughly 1/4 of Sanic's throughput.
- **JSON-large is a bright spot** — Aquilia beats FastAPI by **5.7×** (2,747 vs 480 req/s), suggesting efficient raw JSON serialization without Pydantic overhead.
- As a 0.2.0 framework, there is significant optimization potential.

### Where Aquilia Beats FastAPI

| Scenario | Aquilia | FastAPI | Aquilia Advantage |
|----------|--------:|--------:|------------------:|
| JSON Large | 2,747 | 480 | **+472%** 🔥 |

> On large payload serialization, Aquilia is nearly **6× faster** than FastAPI.

---

## 8. Optimization Roadmap for Aquilia

| Priority | Optimization | Expected Impact |
|----------|-------------|-----------------|
| 🔴 High | Switch to `orjson` or `ujson` for JSON encoding | +50-100% on JSON scenarios |
| 🔴 High | Adopt `httptools` for HTTP parsing | +100-200% on all scenarios |
| 🟡 Medium | Reduce middleware overhead per request | +20-50% across the board |
| 🟡 Medium | Optimize Response object construction | +10-30% |
| 🟢 Low | Connection keep-alive tuning | +5-15% on sustained loads |

---

## 9. Methodology Notes

- All tests ran on the **same Docker host** under identical resource constraints.
- **wrk** was used for all GET scenarios (4 threads, 50 connections, 30s).
- **Median** of 3 runs is reported to smooth variance.
- Docker stats were captured post-benchmark at idle — actual CPU during load was higher.
- Stream scenario is inherently capped by deliberate `asyncio.sleep()` delays and should not be used to compare framework performance.
- These results reflect **Docker-on-Mac** performance. Native Linux may show different absolute numbers but similar relative rankings.

---

## 10. Raw Data

Full raw `wrk` outputs and CSV data are available in:
- `benchmark/results/` — per-framework, per-scenario raw files
- `benchmark/results.csv` — aggregated CSV

### CSV Summary

```
scenario,framework,req_s,p50_ms,p95_ms,p99_ms,errors
ping,aquilia,4543,6.43,46.38,65.79,0
ping,sanic,23522,1.38,22.35,41.00,0
ping,fastapi,19721,1.53,27.50,45.05,0
json,aquilia,4895,5.93,45.02,64.56,0
json,sanic,23404,1.35,23.33,41.12,0
json,fastapi,17691,1.64,29.91,47.23,0
json-large,aquilia,2747,11.14,49.38,92.17,0
json-large,sanic,4000,11.41,14.66,46.13,0
json-large,fastapi,480,97.61,111.50,249.30,0
html,aquilia,4560,6.40,46.30,66.78,0
html,sanic,23697,1.37,22.01,39.76,0
html,fastapi,18763,1.62,26.45,42.21,0
stream,aquilia,16,1540.00,1910.00,1990.00,987
stream,sanic,19,1450.00,1920.00,1980.00,1014
stream,fastapi,19,1040.00,1800.00,1980.00,994
```

---

*Generated by the Aquilia Benchmark Suite — 2026-02-18*
