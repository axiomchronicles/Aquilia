# Framework Shootout Benchmark Suite
## Aquilia vs Sanic vs FastAPI

Reproducible benchmark comparison covering **14 scenarios** that map every public HTTP/WebSocket/streaming feature Aquilia implements.

---

## Quick Start (5 commands)

```bash
# 1. Install load-testing tools
brew install wrk hey        # macOS
# apt install wrk && go install github.com/rakyll/hey@latest  # Linux

# 2. Install Python WebSocket client
pip install websockets

# 3. Deploy all frameworks + PostgreSQL in Docker
./benchmark/bench_scripts/deploy_and_start.sh all

# 4. Run the full benchmark suite (all frameworks, 3 runs each)
./benchmark/bench_scripts/bench_all.sh all

# 5. Generate the final report
python benchmark/bench_scripts/collect_results.py
cat benchmark/final_report.md
```

---

## Prerequisites

| Tool | Install | Purpose |
|------|---------|---------|
| Docker & Docker Compose | [docker.com](https://docker.com) | Run frameworks + PostgreSQL |
| wrk | `brew install wrk` | HTTP GET load testing |
| hey | `brew install hey` | HTTP POST load testing |
| Python 3.11+ | System | Run scripts |
| websockets | `pip install websockets` | WebSocket benchmarking |
| py-spy (optional) | `pip install py-spy` | CPU flamegraphs |

---

## Directory Structure

```
benchmark/
├── README.md                          ← You are here
├── endpoints_discovery.md             ← Aquilia feature audit & parity mapping
├── final_report.md                    ← Report template (populated after run)
├── results.csv                        ← CSV results (generated)
│
├── apps/
│   ├── aquilia_app/
│   │   ├── __init__.py
│   │   ├── main.py                    ← ASGI entry point
│   │   ├── controllers.py            ← All benchmark endpoints
│   │   └── ws_controller.py          ← WebSocket echo controller
│   ├── sanic_app/
│   │   ├── __init__.py
│   │   └── main.py                    ← All endpoints + WS
│   └── fastapi_app/
│       ├── __init__.py
│       └── main.py                    ← All endpoints + WS
│
├── docker/
│   ├── docker-compose.yml             ← Full stack (PG + 3 frameworks)
│   ├── aquilia.Dockerfile
│   ├── sanic.Dockerfile
│   └── fastapi.Dockerfile
│
├── bench_scripts/
│   ├── deploy_and_start.sh            ← Build, seed, start
│   ├── bench_all.sh                   ← Run all scenarios
│   ├── collect_results.py             ← Parse outputs → CSV/Markdown
│   ├── ws_bench.py                    ← WebSocket load generator
│   └── profile_framework.sh          ← py-spy, Docker stats, PG stats
│
├── payloads/
│   ├── json_small.json                ← {"hello":"world"}
│   ├── db_write.json                  ← INSERT payload
│   └── upload_10mb.bin                ← 10MB upload file
│
├── static/
│   └── bench.bin                      ← 100KB static file
│
├── seed_db.py                         ← Database seeding script
│
├── results/                           ← Raw outputs (generated)
│   ├── aquilia/{scenario}/run{1,2,3}.txt
│   ├── sanic/{scenario}/run{1,2,3}.txt
│   └── fastapi/{scenario}/run{1,2,3}.txt
│
└── flamegraphs/                       ← Profiler artifacts (generated)
    ├── {framework}_{scenario}.svg
    ├── {framework}_docker_stats.txt
    ├── {framework}_memory.txt
    └── pg_stats.txt
```

---

## Step-by-Step Guide

### 1. Deploy Infrastructure

```bash
# Start only PostgreSQL + seed
./benchmark/bench_scripts/deploy_and_start.sh postgres

# Start a single framework
./benchmark/bench_scripts/deploy_and_start.sh aquilia

# Start all frameworks
./benchmark/bench_scripts/deploy_and_start.sh all
```

### 2. Verify Endpoints

```bash
# Aquilia
curl http://127.0.0.1:8000/ping          # → pong
curl http://127.0.0.1:8000/json          # → {"hello":"world"}
curl http://127.0.0.1:8000/db/42         # → {"id":42,"name":"user-42",...}

# Sanic
curl http://127.0.0.1:8001/ping
curl http://127.0.0.1:8001/json

# FastAPI
curl http://127.0.0.1:8002/ping
curl http://127.0.0.1:8002/json
```

### 3. Run Benchmarks

```bash
# Single framework
./benchmark/bench_scripts/bench_all.sh aquilia

# All frameworks
./benchmark/bench_scripts/bench_all.sh all
```

### 4. Collect Profiling Data

```bash
./benchmark/bench_scripts/profile_framework.sh aquilia
./benchmark/bench_scripts/profile_framework.sh sanic
./benchmark/bench_scripts/profile_framework.sh fastapi
```

### 5. Generate Report

```bash
# Markdown + CSV
python benchmark/bench_scripts/collect_results.py --output-format both

# View
cat benchmark/final_report.md
```

### 6. Tear Down

```bash
docker compose -f benchmark/docker/docker-compose.yml down -v
```

---

## Benchmark Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Connections | 50 | Moderate concurrency, realistic for single-instance |
| Duration | 3 minutes | Long enough for steady-state, short enough for CI |
| Warmup | 30 seconds | Fills connection pools, JIT caches |
| Runs | 3 | Median eliminates outliers |
| Workers | 4 | Matches common deployment pattern |
| Docker CPUs | 2 | Constrained but realistic |
| Docker Memory | 512 MB | Reveals memory-hungry patterns |
| DB Pool | min=4, max=8 | Balanced for 4 workers × 50 connections |
| DB Rows | 1000 | Fits in PG shared_buffers for consistent reads |

---

## Scenarios Tested

1. **ping** — Minimal response, measures framework overhead
2. **json** — Small JSON serialization
3. **json-large** — Large JSON (≥1MB), tests serializer throughput
4. **html** — Jinja2 template rendering (50 list items)
5. **path** — Dynamic path parameter extraction
6. **query** — Parse 20 query string parameters
7. **db-read** — Single-row read by PK via asyncpg
8. **db-write** — INSERT RETURNING via asyncpg
9. **upload** — 10MB multipart/form-data upload
10. **stream** — Chunked streaming (100×10KB = 1MB)
11. **sse** — Server-Sent Events (50 events)
12. **websocket** — Bi-directional JSON echo (50 conn × 100 msg)
13. **static** — 100KB static file serving
14. **background** — JSON response + background task

---

## CI Integration

All scripts are idempotent. For CI:

```yaml
# GitHub Actions example
- name: Run Benchmark
  run: |
    ./benchmark/bench_scripts/deploy_and_start.sh all
    ./benchmark/bench_scripts/bench_all.sh all
    python benchmark/bench_scripts/collect_results.py --output-format both
    cat benchmark/final_report.md
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `wrk: command not found` | `brew install wrk` |
| `hey: command not found` | `brew install hey` |
| Docker build fails | Ensure Docker Desktop is running |
| DB connection refused | Wait for PostgreSQL health check: `docker compose logs postgres` |
| py-spy fails | Needs `SYS_PTRACE` capability or run as root |
| Upload benchmark slow | Expected — 10MB × 1000 uploads takes ~15-30 min |
| WebSocket benchmark errors | Ensure `websockets` is installed: `pip install websockets` |
