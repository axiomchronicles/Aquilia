#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Spike-load benchmark: ramp from 10 → 500 concurrent over 60 seconds.
# Tests how frameworks degrade under sudden traffic bursts.
#
# Usage:  ./bench/run_spike.sh <framework> <scenario> [run_id]
# Example: ./bench/run_spike.sh aquilia ping 1
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

FRAMEWORK="${1:?Usage: $0 <framework> <scenario> [run_id]}"
SCENARIO="${2:?Usage: $0 <framework> <scenario> [run_id]}"
RUN_ID="${3:-1}"

declare -A PORTS=(
    [flask]=8081  [django]=8082  [fastapi]=8083
    [aquilia]=8084 [sanic]=8085  [tornado]=8086
)

PORT="${PORTS[$FRAMEWORK]}"
BASE="http://localhost:${PORT}"
OUT_DIR="results/${FRAMEWORK}/${SCENARIO}/spike${RUN_ID}"
mkdir -p "$OUT_DIR"

echo "═══ SPIKE: $FRAMEWORK / $SCENARIO  (run=$RUN_ID) ═══"
echo "  Ramp: 10 → 100 → 250 → 500 concurrent over 60s"

# Map scenario to URL and method
case "$SCENARIO" in
    ping)      URL="$BASE/ping";    METHOD="GET"  ;;
    json)      URL="$BASE/json";    METHOD="GET"  ;;
    db-read)   URL="$BASE/db-read?id=42"; METHOD="GET"  ;;
    db-write)  URL="$BASE/db-write"; METHOD="POST" ;;
    upload)    URL="$BASE/upload";   METHOD="POST" ;;
    stream)    URL="$BASE/stream";   METHOD="GET"  ;;
    *)
        echo "  ⚠ Spike load not applicable for scenario: $SCENARIO"
        exit 0
        ;;
esac

# Spike phases: concurrency, duration
PHASES=(
    "10   15"
    "100  15"
    "250  15"
    "500  15"
)

PHASE_NUM=0
for PHASE in "${PHASES[@]}"; do
    read -r CONC DUR <<< "$PHASE"
    PHASE_NUM=$((PHASE_NUM + 1))

    echo "  Phase $PHASE_NUM: ${CONC}c × ${DUR}s ..."

    if [[ "$METHOD" == "GET" ]]; then
        wrk -t4 -c"$CONC" -d"${DUR}s" --latency "$URL" \
            > "$OUT_DIR/phase${PHASE_NUM}_c${CONC}.txt" 2>&1
    else
        # POST with small JSON body
        hey -c "$CONC" -z "${DUR}s" -m POST \
            -H "Content-Type: application/json" \
            -d '{"name":"spike","value":0}' \
            "$URL" \
            > "$OUT_DIR/phase${PHASE_NUM}_c${CONC}.txt" 2>&1
    fi

    # Collect container stats between phases
    docker stats --no-stream --format \
        "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
        | grep "$FRAMEWORK" \
        > "$OUT_DIR/stats_phase${PHASE_NUM}.txt" 2>/dev/null || true
done

echo "  ✓ Spike test complete → $OUT_DIR/"
