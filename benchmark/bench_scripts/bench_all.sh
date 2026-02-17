#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# bench_all.sh — Run the full benchmark suite for one or all frameworks
# ─────────────────────────────────────────────────────────────
# Usage:
#   ./benchmark/bench_scripts/bench_all.sh aquilia
#   ./benchmark/bench_scripts/bench_all.sh sanic
#   ./benchmark/bench_scripts/bench_all.sh fastapi
#   ./benchmark/bench_scripts/bench_all.sh all
#
# Prerequisites:
#   brew install wrk hey  (macOS)
#   apt install wrk       (Linux) + go install github.com/rakyll/hey@latest
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RESULTS_DIR="$PROJECT_ROOT/benchmark/results"
PAYLOADS_DIR="$PROJECT_ROOT/benchmark/payloads"
FRAMEWORK="${1:-all}"

# ── Benchmark parameters (match REPORT spec) ──
THREADS=4
CONNECTIONS=50
DURATION="3m"
WARMUP_DURATION="30s"
RUNS=3
HEY_REQUESTS=100000

# ── Port mapping ──
declare -A PORTS
PORTS[aquilia]=8000
PORTS[sanic]=8001
PORTS[fastapi]=8002

HOST="127.0.0.1"

info()  { echo -e "\033[1;34m[BENCH]\033[0m $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m $*"; }
ts()    { date "+%Y-%m-%d %H:%M:%S"; }

# ── Query string for /search ──
QUERY_STRING="q=benchmark&page=1&limit=20&sort=name&order=asc&category=test&min_price=10&max_price=100&brand=acme&color=red&size=large&material=cotton&rating=4&in_stock=true&free_shipping=true&new_arrival=false&on_sale=true&featured=false&tag=bench&lang=en"

# ── Ensure results directory exists ──
ensure_dir() {
    local fw="$1" scenario="$2"
    mkdir -p "$RESULTS_DIR/$fw/$scenario"
}

# ── Run wrk with warmup ──
run_wrk() {
    local fw="$1" scenario="$2" url="$3" run_num="$4"
    local extra_args="${5:-}"
    ensure_dir "$fw" "$scenario"

    local outfile="$RESULTS_DIR/$fw/$scenario/run${run_num}.txt"

    if [ "$run_num" -eq 1 ]; then
        info "[$fw/$scenario] Warmup (${WARMUP_DURATION})..."
        wrk -t2 -c"$CONNECTIONS" -d"$WARMUP_DURATION" --latency $extra_args "$url" > /dev/null 2>&1 || true
    fi

    info "[$fw/$scenario] Run $run_num (${DURATION})... $(ts)"
    wrk -t"$THREADS" -c"$CONNECTIONS" -d"$DURATION" --latency $extra_args "$url" > "$outfile" 2>&1
    ok "[$fw/$scenario] Run $run_num → $outfile"
}

# ── Run hey for POST ──
run_hey() {
    local fw="$1" scenario="$2" url="$3" run_num="$4"
    local payload_file="${5:-}"
    local content_type="${6:-application/json}"
    ensure_dir "$fw" "$scenario"

    local outfile="$RESULTS_DIR/$fw/$scenario/run${run_num}.txt"

    if [ "$run_num" -eq 1 ]; then
        info "[$fw/$scenario] Warmup (1000 requests)..."
        if [ -n "$payload_file" ]; then
            hey -n 1000 -c "$CONNECTIONS" -m POST \
                -H "Content-Type: $content_type" \
                -D "$payload_file" "$url" > /dev/null 2>&1 || true
        else
            hey -n 1000 -c "$CONNECTIONS" -m POST \
                -H "Content-Type: $content_type" "$url" > /dev/null 2>&1 || true
        fi
    fi

    info "[$fw/$scenario] Run $run_num (${HEY_REQUESTS} requests)... $(ts)"
    if [ -n "$payload_file" ]; then
        hey -n "$HEY_REQUESTS" -c "$CONNECTIONS" -m POST \
            -H "Content-Type: $content_type" \
            -D "$payload_file" "$url" > "$outfile" 2>&1
    else
        hey -n "$HEY_REQUESTS" -c "$CONNECTIONS" -m POST \
            -H "Content-Type: $content_type" "$url" > "$outfile" 2>&1
    fi
    ok "[$fw/$scenario] Run $run_num → $outfile"
}

# ── Run upload benchmark (multipart via curl loop + hey) ──
run_upload() {
    local fw="$1" scenario="$2" url="$3" run_num="$4"
    ensure_dir "$fw" "$scenario"

    local outfile="$RESULTS_DIR/$fw/$scenario/run${run_num}.txt"
    local upload_file="$PAYLOADS_DIR/upload_10mb.bin"

    if [ "$run_num" -eq 1 ]; then
        info "[$fw/$scenario] Warmup (100 uploads)..."
        for i in $(seq 1 100); do
            curl -sf -X POST -F "file=@${upload_file}" "$url" > /dev/null 2>&1 || true
        done
    fi

    info "[$fw/$scenario] Run $run_num (1000 uploads)... $(ts)"
    {
        echo "=== Upload Benchmark: $fw/$scenario run$run_num ==="
        echo "Start: $(ts)"
        local start_time=$(date +%s%N)
        local errors=0
        local total=1000
        for i in $(seq 1 $total); do
            if ! curl -sf -X POST -F "file=@${upload_file}" "$url" > /dev/null 2>&1; then
                errors=$((errors + 1))
            fi
        done
        local end_time=$(date +%s%N)
        local elapsed_ms=$(( (end_time - start_time) / 1000000 ))
        local elapsed_s=$(echo "scale=3; $elapsed_ms / 1000" | bc)
        local rps=$(echo "scale=2; $total / $elapsed_s" | bc)
        echo "End: $(ts)"
        echo "Total requests: $total"
        echo "Errors: $errors"
        echo "Elapsed: ${elapsed_s}s"
        echo "Requests/sec: $rps"
    } > "$outfile" 2>&1
    ok "[$fw/$scenario] Run $run_num → $outfile"
}

# ── WebSocket benchmark ──
run_ws() {
    local fw="$1" scenario="$2" port="$3" run_num="$4"
    ensure_dir "$fw" "$scenario"

    local outfile="$RESULTS_DIR/$fw/$scenario/run${run_num}.txt"

    # Aquilia uses envelope protocol; Sanic/FastAPI use raw JSON
    local ws_protocol="raw"
    if [ "$fw" = "aquilia" ]; then
        ws_protocol="envelope"
    fi

    info "[$fw/$scenario] Run $run_num (WS bench, protocol=$ws_protocol)... $(ts)"
    python3 "$PROJECT_ROOT/benchmark/bench_scripts/ws_bench.py" \
        --host "$HOST" --port "$port" --path "/ws" \
        --connections 50 --messages 100 \
        --protocol "$ws_protocol" \
        > "$outfile" 2>&1
    ok "[$fw/$scenario] Run $run_num → $outfile"
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
    local port="${PORTS[$fw]}"
    local base="http://${HOST}:${port}"

    info "════════════════════════════════════════"
    info "  Benchmarking: $fw (port $port)"
    info "════════════════════════════════════════"

    for run in $(seq 1 $RUNS); do
        info "── Run $run of $RUNS ──"

        # GET scenarios via wrk
        run_wrk "$fw" "ping"       "$base/ping"                         "$run"
        run_wrk "$fw" "json"       "$base/json"                         "$run"
        run_wrk "$fw" "json-large" "$base/json-large"                   "$run"
        run_wrk "$fw" "html"       "$base/html"                         "$run"
        run_wrk "$fw" "path"       "$base/user/42"                      "$run"
        run_wrk "$fw" "query"      "$base/search?${QUERY_STRING}"       "$run"
        run_wrk "$fw" "db-read"    "$base/db/42"                        "$run"
        run_wrk "$fw" "stream"     "$base/stream"                       "$run"
        run_wrk "$fw" "sse"        "$base/sse"                          "$run"
        run_wrk "$fw" "static"     "$base/static/bench.bin"             "$run"
        run_wrk "$fw" "background" "$base/background"                   "$run"

        # POST scenarios via hey
        run_hey "$fw" "db-write" "$base/db" "$run" "$PAYLOADS_DIR/db_write.json"

        # Upload scenario
        run_upload "$fw" "upload" "$base/upload" "$run"

        # WebSocket scenario
        run_ws "$fw" "websocket" "$port" "$run"
    done

    # Docker stats snapshot
    collect_docker_stats "$fw" "bench-$fw"

    ok "All scenarios complete for $fw"
}

# ── Main ──
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

ok "════════════════════════════════════════"
ok "  Benchmark suite complete: $FRAMEWORK"
ok "  Results in: $RESULTS_DIR"
ok "════════════════════════════════════════"
