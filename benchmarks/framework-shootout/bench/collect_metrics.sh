#!/usr/bin/env bash
#
# collect_metrics.sh — Collect CPU/memory stats for all containers.
#
# Usage:
#   ./bench/collect_metrics.sh [duration_seconds] [interval_seconds]
#
# Writes CSV to results/system_metrics.csv
#
set -euo pipefail
cd "$(dirname "$0")/.."

DURATION="${1:-180}"
INTERVAL="${2:-2}"
OUTFILE="results/system_metrics.csv"
mkdir -p results

echo "timestamp,container,cpu_pct,mem_usage,mem_limit,net_in,net_out" > "$OUTFILE"

echo "Collecting container metrics every ${INTERVAL}s for ${DURATION}s..."
echo "Output: $OUTFILE"

END=$((SECONDS + DURATION))
while [ $SECONDS -lt $END ]; do
    TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.NetIO}}" \
        2>/dev/null | while IFS=',' read -r name cpu mem netio; do
            # Parse mem: "123MiB / 512MiB"
            mem_usage=$(echo "$mem" | awk -F'/' '{gsub(/[[:space:]]/, "", $1); print $1}')
            mem_limit=$(echo "$mem" | awk -F'/' '{gsub(/[[:space:]]/, "", $2); print $2}')
            # Parse net: "1.23MB / 4.56MB"
            net_in=$(echo "$netio" | awk -F'/' '{gsub(/[[:space:]]/, "", $1); print $1}')
            net_out=$(echo "$netio" | awk -F'/' '{gsub(/[[:space:]]/, "", $2); print $2}')
            echo "${TS},${name},${cpu},${mem_usage},${mem_limit},${net_in},${net_out}" >> "$OUTFILE"
        done
    sleep "$INTERVAL"
done

echo "Done. $(wc -l < "$OUTFILE") data points collected."
