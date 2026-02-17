# Framework Shootout — Benchmark Report

**Generated:** 2026-02-17 15:45 UTC  
**Frameworks:** flask, django, fastapi, aquilia, sanic, tornado  
**Scenarios:** ping, json, db-read, db-write, upload, stream, websocket, query, path, json-large, html  
**Python:** 3.11 (Docker, 2 CPU / 512MB per container)  

---

## PING

| # | Framework | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Errors | CPU % | Mem (MiB) | Runs |
|---|-----------|------:|--------:|--------:|--------:|------:|------:|--------:|-----:|
| 🥇1 | **sanic** | 38,472 | 0.67 | 0.00 | 50.57 | 0 | 0.0 | 0 | 1 |
| 🥈2 | **fastapi** | 28,280 | 0.93 | 0.00 | 51.02 | 0 | 0.0 | 0 | 1 |
| 🥉3 | **tornado** | 15,547 | 3.08 | 0.00 | 4.14 | 0 | 0.0 | 0 | 1 |
| 4 | **flask** | 6,520 | 4.34 | 0.00 | 61.03 | 0 | 0.0 | 0 | 1 |
| 5 | **django** | 5,898 | 4.93 | 0.00 | 83.76 | 0 | 0.0 | 0 | 1 |
| 6 | **aquilia** | 2,302 | 12.66 | 0.00 | 119.26 | 0 | 0.0 | 0 | 1 |

## JSON

| # | Framework | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Errors | CPU % | Mem (MiB) | Runs |
|---|-----------|------:|--------:|--------:|--------:|------:|------:|--------:|-----:|
| 🥇1 | **sanic** | 35,130 | 0.74 | 0.00 | 52.42 | 0 | 0.0 | 0 | 1 |
| 🥈2 | **fastapi** | 22,569 | 1.19 | 0.00 | 51.98 | 0 | 0.0 | 0 | 1 |
| 🥉3 | **tornado** | 14,078 | 3.29 | 0.00 | 6.83 | 0 | 0.0 | 0 | 1 |
| 4 | **django** | 5,944 | 4.40 | 0.00 | 62.56 | 0 | 0.0 | 0 | 1 |
| 5 | **flask** | 5,722 | 5.00 | 0.00 | 61.91 | 0 | 0.0 | 0 | 1 |
| 6 | **aquilia** | 2,822 | 10.36 | 0.00 | 70.70 | 0 | 0.0 | 0 | 1 |

## DB-READ

| # | Framework | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Errors | CPU % | Mem (MiB) | Runs |
|---|-----------|------:|--------:|--------:|--------:|------:|------:|--------:|-----:|
| 🥇1 | **flask** | 3,903 | 7.63 | 0.00 | 61.41 | 0 | 0.0 | 0 | 1 |
| 🥈2 | **django** | 3,660 | 8.65 | 0.00 | 63.78 | 0 | 0.0 | 0 | 1 |
| 🥉3 | **fastapi** | 2,514 | 12.49 | 0.00 | 738.18 | 2651 | 0.0 | 0 | 1 |
| 4 | **aquilia** | 814 | 61.31 | 0.00 | 266.33 | 748 | 0.0 | 0 | 1 |

## DB-WRITE

| # | Framework | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Errors | CPU % | Mem (MiB) | Runs |
|---|-----------|------:|--------:|--------:|--------:|------:|------:|--------:|-----:|
| 🥇1 | **flask** | 3,909 | 8.00 | 50.00 | 55.30 | 0 | 0.0 | 0 | 1 |
| 🥈2 | **django** | 1,969 | 17.30 | 61.60 | 77.00 | 0 | 0.0 | 0 | 1 |
| 🥉3 | **aquilia** | 426 | 99.20 | 271.10 | 392.40 | 588 | 0.0 | 0 | 1 |

## UPLOAD

| # | Framework | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Errors | CPU % | Mem (MiB) | Runs |
|---|-----------|------:|--------:|--------:|--------:|------:|------:|--------:|-----:|
| 🥇1 | **fastapi** | 441 | 31.20 | 91.60 | 107.00 | 0 | 0.0 | 0 | 1 |
| 🥈2 | **sanic** | 402 | 37.40 | 85.70 | 103.40 | 0 | 0.0 | 0 | 1 |
| 🥉3 | **tornado** | 268 | 63.80 | 135.60 | 276.20 | 0 | 0.0 | 0 | 1 |
| 4 | **aquilia** | 253 | 80.80 | 176.80 | 203.70 | 0 | 0.0 | 0 | 1 |
| 5 | **django** | 177 | 104.00 | 188.80 | 198.00 | 918 | 0.0 | 0 | 1 |
| 6 | **flask** | 116 | 141.10 | 337.30 | 397.20 | 0 | 0.0 | 0 | 1 |

## STREAM

| # | Framework | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Errors | CPU % | Mem (MiB) | Runs |
|---|-----------|------:|--------:|--------:|--------:|------:|------:|--------:|-----:|
| 🥇1 | **sanic** | 893 | 14.56 | 0.00 | 74.67 | 0 | 0.0 | 0 | 1 |
| 🥈2 | **fastapi** | 844 | 15.11 | 0.00 | 74.98 | 0 | 0.0 | 0 | 1 |
| 🥉3 | **django** | 569 | 29.49 | 0.00 | 96.16 | 0 | 0.0 | 0 | 1 |
| 4 | **flask** | 540 | 25.66 | 0.00 | 89.92 | 0 | 0.0 | 0 | 1 |
| 5 | **aquilia** | 497 | 33.30 | 0.00 | 157.86 | 0 | 0.0 | 0 | 1 |
| 6 | **tornado** | 388 | 49.95 | 0.00 | 70.04 | 0 | 0.0 | 0 | 1 |

## QUERY

| # | Framework | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Errors | CPU % | Mem (MiB) | Runs |
|---|-----------|------:|--------:|--------:|--------:|------:|------:|--------:|-----:|
| 🥇1 | **sanic** | 35,608 | 0.79 | 0.00 | 51.18 | 0 | 0.0 | 0 | 1 |
| 🥈2 | **fastapi** | 17,535 | 1.61 | 0.00 | 52.20 | 0 | 0.0 | 0 | 1 |
| 🥉3 | **tornado** | 12,584 | 3.55 | 0.00 | 49.74 | 0 | 0.0 | 0 | 1 |
| 4 | **flask** | 6,198 | 5.18 | 0.00 | 65.00 | 0 | 0.0 | 0 | 1 |
| 5 | **aquilia** | 2,650 | 11.63 | 0.00 | 80.21 | 0 | 0.0 | 0 | 1 |

## PATH

| # | Framework | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Errors | CPU % | Mem (MiB) | Runs |
|---|-----------|------:|--------:|--------:|--------:|------:|------:|--------:|-----:|
| 🥇1 | **sanic** | 40,125 | 0.72 | 0.00 | 51.32 | 0 | 0.0 | 0 | 1 |
| 🥈2 | **fastapi** | 21,376 | 1.30 | 0.00 | 53.31 | 0 | 0.0 | 0 | 1 |
| 🥉3 | **tornado** | 14,863 | 3.17 | 0.00 | 5.06 | 0 | 0.0 | 0 | 1 |
| 4 | **flask** | 6,645 | 6.66 | 0.00 | 65.47 | 0 | 0.0 | 0 | 1 |
| 5 | **aquilia** | 3,283 | 8.83 | 0.00 | 72.39 | 0 | 0.0 | 0 | 1 |

## HTML

| # | Framework | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Errors | CPU % | Mem (MiB) | Runs |
|---|-----------|------:|--------:|--------:|--------:|------:|------:|--------:|-----:|
| 🥇1 | **sanic** | 39,815 | 0.71 | 0.00 | 50.87 | 0 | 0.0 | 0 | 1 |
| 🥈2 | **fastapi** | 26,495 | 1.10 | 0.00 | 51.40 | 0 | 0.0 | 0 | 1 |
| 🥉3 | **tornado** | 15,618 | 3.06 | 0.00 | 3.67 | 0 | 0.0 | 0 | 1 |
| 4 | **flask** | 6,824 | 4.83 | 0.00 | 62.37 | 0 | 0.0 | 0 | 1 |
| 5 | **aquilia** | 3,320 | 8.30 | 0.00 | 104.95 | 0 | 0.0 | 0 | 1 |

---

## Executive Summary

### Winner per Scenario

| Scenario | Winner | Req/s | Runner-up | Req/s |
|----------|--------|------:|-----------|------:|
| ping | **sanic** | 38,472 | fastapi | 28,280 |
| json | **sanic** | 35,130 | fastapi | 22,569 |
| db-read | **flask** | 3,903 | django | 3,660 |
| db-write | **flask** | 3,909 | django | 1,969 |
| upload | **fastapi** | 441 | sanic | 402 |
| stream | **sanic** | 893 | fastapi | 844 |
| query | **sanic** | 35,608 | fastapi | 17,535 |
| path | **sanic** | 40,125 | fastapi | 21,376 |
| html | **sanic** | 39,815 | fastapi | 26,495 |

### Overall Winner: **sanic** (6/11 scenarios)

### Analysis Notes

- **Ping/JSON** (tiny payload): Measures pure request-routing overhead.
  Async frameworks (FastAPI, Aquilia, Sanic) typically dominate due to
  event-loop efficiency vs. gunicorn process model.

- **DB-read/write**: Async frameworks using `asyncpg` have an advantage
  over sync frameworks using `psycopg2` with thread pools.

- **Upload**: Tests I/O handling. Memory consumption matters here.

- **Stream**: Tests chunked transfer. Async generators are natural fit.

- **WebSocket**: Only async frameworks support this natively.
  Flask and Django are excluded from this scenario.

---

## Methodology

- **Isolation:** Each framework runs in its own Docker container (2 CPU, 512MB).
- **DB:** PostgreSQL 16 with shared schema and 1000 seeded rows.
- **Workers:** Sync (Flask/Django): gunicorn 4w×2t. Async: uvicorn/sanic 4 workers.
- **Load:** `wrk` for GET, `hey` for POST. 50 concurrent, 3 min steady-state.
- **Warmup:** 30s before each measurement.
- **Repetitions:** 3 runs per scenario, median reported.
- **Correctness:** Each endpoint validated before load test.
