#!/usr/bin/env bash
#
# run_scenario.sh — Run a single benchmark scenario against a single framework.
#
# Usage:
#   ./bench/run_scenario.sh <framework> <scenario> [run_id]
#
# Examples:
#   ./bench/run_scenario.sh fastapi ping 1
#   ./bench/run_scenario.sh flask db-read 2
#
set -euo pipefail

FRAMEWORK="${1:?Usage: $0 <framework> <scenario> [run_id]}"
SCENARIO="${2:?Usage: $0 <framework> <scenario> [run_id]}"
RUN_ID="${3:-1}"

# Port mapping
declare -A PORTS=(
    [flask]=8081
    [django]=8082
    [fastapi]=8083
    [aquilia]=8084
    [sanic]=8085
    [tornado]=8086
)

PORT="${PORTS[$FRAMEWORK]}"
HOST="localhost"
BASE="http://${HOST}:${PORT}"
RESULTS_DIR="results/${FRAMEWORK}/${SCENARIO}/run${RUN_ID}"
mkdir -p "$RESULTS_DIR"

DURATION_STEADY="180s"
DURATION_WARMUP="30s"
CONNS_STEADY=50
THREADS=4

# Upload test file (5 MB)
UPLOAD_FILE="/tmp/bench_upload_5mb.bin"
if [[ ! -f "$UPLOAD_FILE" ]]; then
    dd if=/dev/urandom of="$UPLOAD_FILE" bs=1M count=5 2>/dev/null
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Framework: $FRAMEWORK  |  Scenario: $SCENARIO  |  Run: $RUN_ID"
echo "  Target: $BASE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Correctness check ────────────────────────────────────────────────────
echo "[1/4] Correctness check..."
case "$SCENARIO" in
    ping)
        RESP=$(curl -s "${BASE}/ping")
        if [[ "$RESP" != "pong" ]]; then
            echo "  FAIL: Expected 'pong', got '$RESP'"
            exit 1
        fi
        echo "  OK: $RESP"
        ;;
    json)
        RESP=$(curl -s "${BASE}/json")
        echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'message' in d and 'ts' in d, f'Bad JSON: {d}'" 2>&1
        echo "  OK: $RESP"
        ;;
    db-read)
        RESP=$(curl -s "${BASE}/db-read?id=1")
        echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'id' in d, f'Bad row: {d}'" 2>&1
        echo "  OK: $RESP"
        ;;
    db-write)
        RESP=$(curl -s -X POST -H 'Content-Type: application/json' \
            -d '{"name":"bench-test","description":"test","price":9.99}' \
            "${BASE}/db-write")
        echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'id' in d, f'Bad write: {d}'" 2>&1
        echo "  OK: $RESP"
        ;;
    upload)
        RESP=$(curl -s -X POST -F "file=@${UPLOAD_FILE}" "${BASE}/upload")
        echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'sha256' in d, f'Bad upload: {d}'" 2>&1
        echo "  OK: sha256 returned"
        ;;
    stream)
        SIZE=$(curl -s "${BASE}/stream" | wc -c | tr -d ' ')
        EXPECTED=$((10 * 1024 * 1024))
        if [[ "$SIZE" -ne "$EXPECTED" ]]; then
            echo "  FAIL: Expected ${EXPECTED} bytes, got ${SIZE}"
            exit 1
        fi
        echo "  OK: ${SIZE} bytes streamed"
        ;;
    websocket)
        echo "  SKIP (correctness): WS tested separately"
        ;;
    *)
        echo "Unknown scenario: $SCENARIO"
        exit 1
        ;;
esac

# ── Warmup ───────────────────────────────────────────────────────────────
echo "[2/4] Warming up (${DURATION_WARMUP})..."
case "$SCENARIO" in
    ping)      wrk -t2 -c10 -d"$DURATION_WARMUP" "${BASE}/ping" > /dev/null 2>&1 ;;
    json)      wrk -t2 -c10 -d"$DURATION_WARMUP" "${BASE}/json" > /dev/null 2>&1 ;;
    db-read)   wrk -t2 -c10 -d"$DURATION_WARMUP" "${BASE}/db-read?id=1" > /dev/null 2>&1 ;;
    db-write)
        # Use hey for POST warmup
        hey -n 500 -c 10 -m POST \
            -H "Content-Type: application/json" \
            -d '{"name":"warmup","description":"warmup","price":1.0}' \
            "${BASE}/db-write" > /dev/null 2>&1
        ;;
    upload)
        hey -n 50 -c 5 -m POST \
            -D "$UPLOAD_FILE" \
            -H "Content-Type: application/octet-stream" \
            "${BASE}/upload" > /dev/null 2>&1
        ;;
    stream)    wrk -t2 -c5 -d10s "${BASE}/stream" > /dev/null 2>&1 ;;
    websocket) echo "  (warmup skipped for WS)" ;;
esac
echo "  Done."

# ── Collect system baseline ──────────────────────────────────────────────
echo "[3/4] Collecting container stats..."
docker stats --no-stream --format \
    "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
    | grep -i "$FRAMEWORK" > "${RESULTS_DIR}/stats_before.txt" 2>/dev/null || true

# ── Steady-state load ────────────────────────────────────────────────────
echo "[4/4] Running steady-state load (${CONNS_STEADY}c, ${DURATION_STEADY})..."
case "$SCENARIO" in
    ping)
        wrk -t"$THREADS" -c"$CONNS_STEADY" -d"$DURATION_STEADY" \
            --latency "${BASE}/ping" \
            > "${RESULTS_DIR}/wrk_steady.txt" 2>&1
        ;;
    json)
        wrk -t"$THREADS" -c"$CONNS_STEADY" -d"$DURATION_STEADY" \
            --latency "${BASE}/json" \
            > "${RESULTS_DIR}/wrk_steady.txt" 2>&1
        ;;
    db-read)
        wrk -t"$THREADS" -c"$CONNS_STEADY" -d"$DURATION_STEADY" \
            --latency "${BASE}/db-read?id=1" \
            > "${RESULTS_DIR}/wrk_steady.txt" 2>&1
        ;;
    db-write)
        hey -z "$DURATION_STEADY" -c "$CONNS_STEADY" \
            -m POST \
            -H "Content-Type: application/json" \
            -d '{"name":"bench-item","description":"benchmark","price":42.00}' \
            "${BASE}/db-write" \
            > "${RESULTS_DIR}/hey_steady.txt" 2>&1
        ;;
    upload)
        hey -z "$DURATION_STEADY" -c 20 \
            -m POST \
            -D "$UPLOAD_FILE" \
            -H "Content-Type: application/octet-stream" \
            "${BASE}/upload" \
            > "${RESULTS_DIR}/hey_steady.txt" 2>&1
        ;;
    stream)
        wrk -t"$THREADS" -c20 -d"$DURATION_STEADY" \
            --latency "${BASE}/stream" \
            > "${RESULTS_DIR}/wrk_steady.txt" 2>&1
        ;;
    websocket)
        echo "  WS: connect 50 parallel sockets, echo for 60s"
        python3 bench/ws_bench.py "${HOST}" "${PORT}" 50 60 \
            > "${RESULTS_DIR}/ws_steady.txt" 2>&1
        ;;
esac

# ── Post-load stats ──────────────────────────────────────────────────────
docker stats --no-stream --format \
    "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
    | grep -i "$FRAMEWORK" > "${RESULTS_DIR}/stats_after.txt" 2>/dev/null || true

echo "  Results → ${RESULTS_DIR}/"
echo "  Done ✓"
