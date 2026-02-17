#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Flamegraph profiling with py-spy.
#
# Captures a CPU profile of a framework container during live load,
# then generates an SVG flamegraph.
#
# Prerequisites:
#   pip install py-spy   (on the host)
#   Docker must be accessible
#
# Usage:  ./bench/profile.sh <framework> <scenario> [duration_s]
# Example: ./bench/profile.sh aquilia ping 30
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

FRAMEWORK="${1:?Usage: $0 <framework> <scenario> [duration]}"
SCENARIO="${2:?Usage: $0 <framework> <scenario> [duration]}"
DURATION="${3:-30}"

declare -A PORTS=(
    [flask]=8081  [django]=8082  [fastapi]=8083
    [aquilia]=8084 [sanic]=8085  [tornado]=8086
)

PORT="${PORTS[$FRAMEWORK]}"
BASE="http://localhost:${PORT}"
OUT_DIR="results/${FRAMEWORK}/profiles"
mkdir -p "$OUT_DIR"

# Get container ID
CONTAINER=$(docker compose ps -q "$FRAMEWORK" 2>/dev/null || true)
if [[ -z "$CONTAINER" ]]; then
    echo "  ✗ Container '$FRAMEWORK' not running."
    exit 1
fi

# Get the PID of the main Python process inside the container
PID=$(docker exec "$CONTAINER" pgrep -f "python|gunicorn|uvicorn|sanic" | head -1)
if [[ -z "$PID" ]]; then
    echo "  ✗ Could not find Python process in container."
    exit 1
fi

echo "═══ PROFILE: $FRAMEWORK / $SCENARIO  (${DURATION}s) ═══"
echo "  Container: $CONTAINER"
echo "  PID: $PID"

# Determine URL for load generation
case "$SCENARIO" in
    ping)      URL="$BASE/ping"         ;;
    json)      URL="$BASE/json"         ;;
    db-read)   URL="$BASE/db-read?id=42";;
    stream)    URL="$BASE/stream"       ;;
    *)         URL="$BASE/ping"         ;;
esac

SVG_FILE="$OUT_DIR/${SCENARIO}_flamegraph.svg"
RAW_FILE="$OUT_DIR/${SCENARIO}_profile.raw"

# Start load in background
echo "  Starting load: wrk -t2 -c50 -d${DURATION}s $URL"
wrk -t2 -c50 -d"${DURATION}s" "$URL" > /dev/null 2>&1 &
WRK_PID=$!

# Run py-spy against the container's PID namespace
echo "  Profiling with py-spy for ${DURATION}s ..."
sudo py-spy record \
    --pid "$PID" \
    --duration "$DURATION" \
    --output "$SVG_FILE" \
    --format flamegraph \
    --subprocesses \
    2>&1 | tail -3 || {
        echo "  ⚠ py-spy failed. Try: sudo py-spy (requires root for container PID namespace)"
        kill $WRK_PID 2>/dev/null || true
        exit 1
    }

# Wait for wrk to finish
wait $WRK_PID 2>/dev/null || true

echo "  ✓ Flamegraph → $SVG_FILE"
echo "  Open in browser: file://$(pwd)/$SVG_FILE"
