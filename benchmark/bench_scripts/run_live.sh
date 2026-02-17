#!/bin/bash
# ─────────────────────────────────────────────────────────────
# run_live.sh — Run benchmarks against already-running containers
# ─────────────────────────────────────────────────────────────
# Targets:
#   aquilia → 127.0.0.1:8084
#   sanic   → 127.0.0.1:8085
#   fastapi → 127.0.0.1:8083
#
# Available endpoints (confirmed): /ping /json /json-large /html /stream
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RESULTS_DIR="$PROJECT_ROOT/benchmark/results"
FRAMEWORK="${1:-all}"

# ── Benchmark parameters ──
THREADS=4
CONNECTIONS=50
DURATION="30s"
WARMUP_DURATION="10s"
RUNS=3

# ── Port mapping (live containers) ──
HOST="127.0.0.1"

get_port() {
    case "$1" in
        aquilia) echo 8084 ;;
        sanic)   echo 8085 ;;
        fastapi) echo 8083 ;;
    esac
}

info()  { echo -e "\033[1;34m[BENCH]\033[0m $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m $*"; }
ts()    { date "+%Y-%m-%d %H:%M:%S"; }

# ── Verify tools ──
for tool in wrk hey curl; do
    if ! command -v "$tool" &>/dev/null; then
        echo "ERROR: $tool not found. Install it first." >&2
        exit 1
    fi
done

# ── Ensure results directory exists ──
ensure_dir() {
    local fw="$1" scenario="$2"
    mkdir -p "$RESULTS_DIR/$fw/$scenario"
}

# ── Run wrk with warmup ──
run_wrk() {
    local fw="$1" scenario="$2" url="$3" run_num="$4"
    ensure_dir "$fw" "$scenario"
    local outfile="$RESULTS_DIR/$fw/$scenario/run${run_num}.txt"

    if [ "$run_num" -eq 1 ]; then
        info "[$fw/$scenario] Warmup (${WARMUP_DURATION})..."
        wrk -t2 -c"$CONNECTIONS" -d"$WARMUP_DURATION" --latency "$url" > /dev/null 2>&1 || true
    fi

    info "[$fw/$scenario] Run $run_num (${DURATION})... $(ts)"
    wrk -t"$THREADS" -c"$CONNECTIONS" -d"$DURATION" --latency "$url" > "$outfile" 2>&1
    ok "[$fw/$scenario] Run $run_num complete"
}

# ── Collect Docker stats snapshot ──
collect_docker_stats() {
    local fw="$1" container="$2"
    ensure_dir "$fw" "docker_stats"
    docker stats --no-stream "$container" \
        > "$RESULTS_DIR/$fw/docker_stats/snapshot.txt" 2>&1 || true
}

# ── Run all scenarios for one framework ──
bench_framework() {
    local fw="$1"
    local port
    port=$(get_port "$fw")
    local base="http://${HOST}:${port}"

    # Verify the framework is up
    if ! curl -sf "$base/ping" > /dev/null 2>&1; then
        warn "$fw on port $port not responding — skipping"
        return 1
    fi

    info "════════════════════════════════════════"
    info "  Benchmarking: $fw (port $port)"
    info "════════════════════════════════════════"

    for run in $(seq 1 $RUNS); do
        info "── Run $run of $RUNS ──"

        run_wrk "$fw" "ping"       "$base/ping"       "$run"
        run_wrk "$fw" "json"       "$base/json"       "$run"
        run_wrk "$fw" "json-large" "$base/json-large"  "$run"
        run_wrk "$fw" "html"       "$base/html"       "$run"
        run_wrk "$fw" "stream"     "$base/stream"     "$run"
    done

    # Docker stats snapshot — try to find the container
    local container
    container=$(docker ps --format '{{.Names}}' | grep -i "$fw" | head -1 || true)
    if [ -n "$container" ]; then
        collect_docker_stats "$fw" "$container"
    fi

    ok "All scenarios complete for $fw"
}

# ── Main ──
info "Benchmark Start: $(ts)"
info "Parameters: ${THREADS} threads, ${CONNECTIONS} connections, ${DURATION} duration, ${WARMUP_DURATION} warmup, ${RUNS} runs"
echo ""

case "$FRAMEWORK" in
    aquilia|sanic|fastapi)
        bench_framework "$FRAMEWORK"
        ;;
    all)
        for fw in aquilia sanic fastapi; do
            bench_framework "$fw"
        done
        ;;
    *)
        echo "Usage: $0 {aquilia|sanic|fastapi|all}"
        exit 1
        ;;
esac

info "Benchmark End: $(ts)"
ok "════════════════════════════════════════"
ok "  Benchmark suite complete: $FRAMEWORK"
ok "  Results in: $RESULTS_DIR"
ok "════════════════════════════════════════"
