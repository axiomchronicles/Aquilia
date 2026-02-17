#!/usr/bin/env bash
#
# run_all.sh — Master orchestrator for the framework shootout.
#
# Runs all scenarios × all frameworks × 3 repetitions.
# Prerequisites: docker compose services running, wrk and hey installed.
#
set -euo pipefail
cd "$(dirname "$0")/.."

FRAMEWORKS=(flask django fastapi aquilia sanic tornado)
SCENARIOS=(ping json db-read db-write upload stream websocket)
RUNS=3

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          Framework Shootout — Benchmark Suite               ║"
echo "║  Frameworks: ${#FRAMEWORKS[@]}  |  Scenarios: ${#SCENARIOS[@]}  |  Runs: $RUNS   ║"
echo "║  Total tests: $(( ${#FRAMEWORKS[@]} * ${#SCENARIOS[@]} * $RUNS ))                                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Pre-flight checks ────────────────────────────────────────────────────
echo "Pre-flight checks..."
for cmd in wrk hey curl python3; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "  ERROR: '$cmd' not found. Install it first."
        exit 1
    fi
done

# Check services are up
declare -A PORTS=(
    [flask]=8081 [django]=8082 [fastapi]=8083
    [aquilia]=8084 [sanic]=8085 [tornado]=8086
)

for fw in "${FRAMEWORKS[@]}"; do
    PORT="${PORTS[$fw]}"
    if ! curl -sf "http://localhost:${PORT}/ping" > /dev/null 2>&1; then
        echo "  WARNING: $fw (port $PORT) not responding. Skipping."
        FRAMEWORKS=("${FRAMEWORKS[@]/$fw/}")
    else
        echo "  ✓ $fw (port $PORT)"
    fi
done
echo ""

# ── Create upload test file ──────────────────────────────────────────────
if [[ ! -f /tmp/bench_upload_5mb.bin ]]; then
    dd if=/dev/urandom of=/tmp/bench_upload_5mb.bin bs=1M count=5 2>/dev/null
    echo "Created 5MB test upload file."
fi

# ── Run benchmarks ───────────────────────────────────────────────────────
TOTAL=0
FAILED=0

for run in $(seq 1 "$RUNS"); do
    echo ""
    echo "═══════════════ Run $run / $RUNS ═══════════════"
    for scenario in "${SCENARIOS[@]}"; do
        for fw in "${FRAMEWORKS[@]}"; do
            [[ -z "$fw" ]] && continue
            echo ""
            TOTAL=$((TOTAL + 1))
            if ! bash bench/run_scenario.sh "$fw" "$scenario" "$run"; then
                echo "  FAILED: $fw / $scenario / run $run"
                FAILED=$((FAILED + 1))
            fi
        done
    done
done

echo ""
echo "════════════════════════════════════════════════════"
echo "  Complete: $TOTAL tests, $FAILED failures"
echo "════════════════════════════════════════════════════"

# ── Generate report ──────────────────────────────────────────────────────
echo ""
echo "Generating report..."
python3 bench/generate_report.py
echo "Report → report/REPORT.md"
