#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# profile_framework.sh — Collect CPU/memory profiles for a framework
# ─────────────────────────────────────────────────────────────
# Usage:
#   ./benchmark/bench_scripts/profile_framework.sh aquilia
#   ./benchmark/bench_scripts/profile_framework.sh sanic
#   ./benchmark/bench_scripts/profile_framework.sh fastapi
#
# Prerequisites:
#   pip install py-spy scalene
#   brew install wrk
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FLAMEGRAPH_DIR="$PROJECT_ROOT/benchmark/flamegraphs"
FRAMEWORK="${1:?Usage: $0 <aquilia|sanic|fastapi>}"

mkdir -p "$FLAMEGRAPH_DIR"

# ── Port mapping ──
declare -A PORTS
PORTS[aquilia]=8000
PORTS[sanic]=8001
PORTS[fastapi]=8002

PORT="${PORTS[$FRAMEWORK]}"
HOST="127.0.0.1"
CONTAINER="bench-$FRAMEWORK"

info()  { echo -e "\033[1;34m[PROFILE]\033[0m $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m $*"; }

# ── Collect Docker stats during load ──
collect_docker_stats() {
    local output="$FLAMEGRAPH_DIR/${FRAMEWORK}_docker_stats.txt"
    info "Collecting Docker stats for $CONTAINER..."
    {
        echo "=== Docker Stats: $FRAMEWORK ==="
        echo "Timestamp: $(date)"
        echo ""
        docker stats --no-stream "$CONTAINER"
        echo ""
        docker exec "$CONTAINER" sh -c 'cat /proc/self/status 2>/dev/null || true'
        echo ""
        docker exec "$CONTAINER" sh -c 'cat /sys/fs/cgroup/memory.current 2>/dev/null || cat /sys/fs/cgroup/memory/memory.usage_in_bytes 2>/dev/null || echo "N/A"'
        echo ""
        docker exec "$CONTAINER" sh -c 'cat /sys/fs/cgroup/cpu.stat 2>/dev/null || cat /sys/fs/cgroup/cpu/cpuacct.usage 2>/dev/null || echo "N/A"'
    } > "$output" 2>&1
    ok "Docker stats → $output"
}

# ── py-spy flamegraph (attach to running container process) ──
collect_pyspy() {
    local scenario="${1:-ping}"
    local output="$FLAMEGRAPH_DIR/${FRAMEWORK}_${scenario}.svg"

    info "Collecting py-spy flamegraph for $FRAMEWORK/$scenario..."

    # Get the main worker PID inside the container
    local pid
    pid=$(docker exec "$CONTAINER" sh -c 'pgrep -f "uvicorn\|sanic" | head -1' 2>/dev/null || echo "")

    if [ -z "$pid" ]; then
        info "Cannot find worker PID, attempting docker top..."
        docker top "$CONTAINER" > "$FLAMEGRAPH_DIR/${FRAMEWORK}_processes.txt" 2>&1
        info "Skipping py-spy (no PID found)"
        return
    fi

    # Start load in background
    wrk -t4 -c50 -d30s --latency "http://${HOST}:${PORT}/${scenario}" &
    local wrk_pid=$!

    # Record flamegraph via docker exec (py-spy must be installed in container)
    docker exec "$CONTAINER" sh -c \
        "pip install py-spy -q 2>/dev/null; py-spy record -o /tmp/${FRAMEWORK}_${scenario}.svg --pid $pid -d 25 --format flamegraph" 2>/dev/null || {
        info "py-spy not available in container, trying host-level..."
        # Attempt from host (requires SYS_PTRACE)
        sudo py-spy record -o "$output" --pid "$(docker inspect --format '{{.State.Pid}}' "$CONTAINER")" -d 25 --format flamegraph 2>/dev/null || {
            info "py-spy failed (needs SYS_PTRACE). Skipping."
            wait "$wrk_pid" 2>/dev/null || true
            return
        }
    }

    # Copy flamegraph out of container
    docker cp "$CONTAINER:/tmp/${FRAMEWORK}_${scenario}.svg" "$output" 2>/dev/null || true

    wait "$wrk_pid" 2>/dev/null || true
    ok "Flamegraph → $output"
}

# ── Memory snapshot via tracemalloc ──
collect_memory() {
    local output="$FLAMEGRAPH_DIR/${FRAMEWORK}_memory.txt"
    info "Collecting memory snapshot for $FRAMEWORK..."

    docker exec "$CONTAINER" python3 -c "
import tracemalloc
tracemalloc.start()
import importlib
# Trigger import of the app module
try:
    if '$FRAMEWORK' == 'aquilia':
        import benchmark.apps.aquilia_app.main
    elif '$FRAMEWORK' == 'sanic':
        import benchmark.apps.sanic_app.main
    elif '$FRAMEWORK' == 'fastapi':
        import benchmark.apps.fastapi_app.main
except Exception:
    pass
snapshot = tracemalloc.take_snapshot()
stats = snapshot.statistics('lineno')[:30]
for s in stats:
    print(s)
" > "$output" 2>&1 || {
    info "tracemalloc snapshot failed (may need app context). Recording container memory instead."
    docker exec "$CONTAINER" sh -c 'ps aux --sort=-%mem | head -20' > "$output" 2>&1 || true
}
    ok "Memory snapshot → $output"
}

# ── Collect PostgreSQL metrics ──
collect_pg_stats() {
    local output="$FLAMEGRAPH_DIR/pg_stats.txt"
    info "Collecting PostgreSQL stats..."
    {
        echo "=== pg_stat_activity ==="
        docker exec benchmark-postgres psql -U bench -d bench -c \
            "SELECT pid, state, query, wait_event_type, wait_event FROM pg_stat_activity WHERE datname='bench';" 2>/dev/null || echo "N/A"
        echo ""
        echo "=== pg_stat_user_tables ==="
        docker exec benchmark-postgres psql -U bench -d bench -c \
            "SELECT relname, seq_scan, idx_scan, n_tup_ins, n_tup_upd, n_tup_del FROM pg_stat_user_tables WHERE relname='bench_users';" 2>/dev/null || echo "N/A"
        echo ""
        echo "=== Connection count ==="
        docker exec benchmark-postgres psql -U bench -d bench -c \
            "SELECT count(*) as connections FROM pg_stat_activity WHERE datname='bench';" 2>/dev/null || echo "N/A"
    } > "$output" 2>&1
    ok "PG stats → $output"
}

# ── Main ──
info "════════════════════════════════════════"
info "  Profiling: $FRAMEWORK"
info "════════════════════════════════════════"

collect_docker_stats
collect_pyspy "ping"
collect_pyspy "json"
collect_pyspy "db-read"
collect_memory
collect_pg_stats

ok "Profiling complete for $FRAMEWORK"
ok "Artifacts in: $FLAMEGRAPH_DIR"
