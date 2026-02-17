# Framework Shootout — Reproducible Benchmark Suite

Apples-to-apples benchmark comparing **Flask, Django, FastAPI, Aquilia, Sanic, Tornado** across 7 scenarios with identical application logic, payloads, and DB schema.

## Quick Start

```bash
cd benchmarks/framework-shootout
docker compose up -d --build
# Wait for services to be healthy (~30s)
./bench/run_all.sh
# Results appear in results/
```

## Architecture

```
┌──────────────────────────────────────────────┐
│              Load Generator (wrk/hey)        │
│              bench/ scripts                  │
└──────────┬───────────────────────────────────┘
           │ HTTP / WebSocket
    ┌──────┴──────────────────────────────┐
    │  Framework Containers (port 8080)   │
    │  flask | django | fastapi | aquilia │
    │  sanic | tornado                    │
    └──────┬──────────────────────────────┘
           │ SQL
    ┌──────┴──────────┐
    │   PostgreSQL    │
    │   Port 5432     │
    └─────────────────┘
```

## Scenarios

| # | Endpoint | Method | Description |
|---|----------|--------|-------------|
| 1 | `/ping` | GET | Returns `pong` — measures request overhead |
| 2 | `/json` | GET | Returns `{"message":"hello","ts":"..."}` — JSON serialization |
| 3 | `/db-read?id=N` | GET | Single-row SELECT by PK |
| 4 | `/db-write` | POST | Single-row INSERT, returns created ID |
| 5 | `/upload` | POST | Accepts 5MB file, returns SHA256 |
| 6 | `/stream` | GET | Streams 10MB response in 64KB chunks |
| 7 | `/ws-echo` | WS | WebSocket echo (frameworks that support it) |

## Load Patterns

- **Steady:** 50 concurrent connections, 3 minutes
- **Spike:** Ramp 10→500 over 60s, hold 2 min, cool down

## Collected Metrics

- Throughput (req/s)
- Latency: p50, p95, p99
- CPU % per container
- Memory RSS per container
- Flamegraphs (py-spy)

## File Structure

```
framework-shootout/
├── docker-compose.yml          # 6 framework containers + PostgreSQL
├── README.md
├── apps/
│   ├── shared/
│   │   ├── Dockerfile          # Generic Python 3.11-slim builder
│   │   └── init.sql            # DB schema + 1000 seed rows
│   ├── flask_app/              # Flask + gunicorn + psycopg2
│   │   ├── app.py
│   │   └── requirements.txt
│   ├── django_app/             # Django minimal + gunicorn + psycopg2
│   │   ├── app.py
│   │   └── requirements.txt
│   ├── fastapi_app/            # FastAPI + uvicorn + asyncpg
│   │   ├── app.py
│   │   └── requirements.txt
│   ├── aquilia_app/            # Aquilia raw ASGI + uvicorn + asyncpg
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   └── Dockerfile          # Custom (installs from local source)
│   ├── sanic_app/              # Sanic built-in server + asyncpg
│   │   ├── app.py
│   │   └── requirements.txt
│   └── tornado_app/            # Tornado + psycopg2 thread pool
│       ├── app.py
│       └── requirements.txt
├── bench/
│   ├── run_all.sh              # Master orchestrator (3 runs × 7 scenarios × 6 frameworks)
│   ├── run_scenario.sh         # Per-scenario runner (correctness → warmup → steady)
│   ├── run_spike.sh            # Spike load: 10→100→250→500 concurrent ramp
│   ├── collect_metrics.sh      # Docker stats CSV collector
│   ├── generate_report.py      # Parse results → Markdown + CSV + JSON report
│   ├── ws_bench.py             # Async WebSocket benchmark client
│   └── profile.sh              # py-spy flamegraph capture
├── results/                    # Raw outputs (gitignored)
│   └── .gitignore
└── report/                     # Generated reports
```

## Port Mapping

| Framework | External Port |
|-----------|:------------:|
| Flask     | 8081         |
| Django    | 8082         |
| FastAPI   | 8083         |
| Aquilia   | 8084         |
| Sanic     | 8085         |
| Tornado   | 8086         |

## Prerequisites

- Docker & Docker Compose v2
- `wrk` — HTTP benchmark tool (`brew install wrk`)
- `hey` — HTTP load generator (`brew install hey`)
- Python 3.8+ with `websockets` (`pip install websockets`) for WS scenario
- (Optional) `py-spy` for flamegraphs (`pip install py-spy`)

## Individual Commands

```bash
# Run one scenario for one framework:
./bench/run_scenario.sh aquilia ping 1

# Spike load test:
./bench/run_spike.sh aquilia json 1

# CPU flamegraph:
./bench/profile.sh aquilia ping 30

# Generate report from existing results:
python3 bench/generate_report.py

# Collect container resource usage:
./bench/collect_metrics.sh results/metrics.csv 1 5
```
