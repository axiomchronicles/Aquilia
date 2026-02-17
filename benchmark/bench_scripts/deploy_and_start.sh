#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# deploy_and_start.sh — Build, seed, and start a benchmark target
# ─────────────────────────────────────────────────────────────
# Usage:
#   ./benchmark/bench_scripts/deploy_and_start.sh aquilia
#   ./benchmark/bench_scripts/deploy_and_start.sh sanic
#   ./benchmark/bench_scripts/deploy_and_start.sh fastapi
#   ./benchmark/bench_scripts/deploy_and_start.sh all
#   ./benchmark/bench_scripts/deploy_and_start.sh postgres   # DB only
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/benchmark/docker/docker-compose.yml"
FRAMEWORK="${1:-all}"

export COMPOSE_PROJECT_NAME=benchshootout

info()  { echo -e "\033[1;34m[INFO]\033[0m $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m $*"; }
err()   { echo -e "\033[1;31m[ERR]\033[0m $*" >&2; }

# ── Helper: wait for HTTP health ──
wait_http() {
    local url="$1" max_wait="${2:-30}" i=0
    info "Waiting for $url ..."
    while ! curl -sf "$url" > /dev/null 2>&1; do
        sleep 1
        i=$((i + 1))
        if [ "$i" -ge "$max_wait" ]; then
            err "Timeout waiting for $url"
            return 1
        fi
    done
    ok "$url is up"
}

# ── Step 1: Start PostgreSQL ──
start_postgres() {
    info "Starting PostgreSQL..."
    docker compose -f "$COMPOSE_FILE" up -d postgres
    sleep 3  # let PG finish init
    ok "PostgreSQL is running"
}

# ── Step 2: Seed database ──
seed_db() {
    info "Seeding database..."
    docker compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -U bench -d bench -c "SELECT 1 FROM bench_users LIMIT 1;" 2>/dev/null && {
        ok "Database already seeded"
        return 0
    }
    # Run seed from host (requires asyncpg installed locally) or via container
    cd "$PROJECT_ROOT"
    DATABASE_URL="postgresql://bench:bench@127.0.0.1:5432/bench" \
        python -m benchmark.seed_db || {
        # Fallback: run inside a temp container
        info "Running seed inside container..."
        docker run --rm --network benchshootout_default \
            -e DATABASE_URL="postgresql://bench:bench@postgres:5432/bench" \
            -v "$PROJECT_ROOT:/app" -w /app \
            python:3.11-slim \
            bash -c "pip install asyncpg -q && python -m benchmark.seed_db"
    }
    ok "Database seeded"
}

# ── Step 3: Build & start framework ──
start_framework() {
    local fw="$1"
    info "Building and starting $fw..."
    docker compose -f "$COMPOSE_FILE" up -d --build "$fw"

    case "$fw" in
        aquilia) wait_http "http://127.0.0.1:8000/ping" ;;
        sanic)   wait_http "http://127.0.0.1:8001/ping" ;;
        fastapi) wait_http "http://127.0.0.1:8002/ping" ;;
    esac
    ok "$fw is running"
}

# ── Main ──
case "$FRAMEWORK" in
    postgres)
        start_postgres
        seed_db
        ;;
    aquilia|sanic|fastapi)
        start_postgres
        seed_db
        start_framework "$FRAMEWORK"
        ;;
    all)
        start_postgres
        seed_db
        for fw in aquilia sanic fastapi; do
            start_framework "$fw"
        done
        ;;
    *)
        err "Unknown framework: $FRAMEWORK"
        echo "Usage: $0 {aquilia|sanic|fastapi|all|postgres}"
        exit 1
        ;;
esac

ok "Deploy complete for: $FRAMEWORK"
