#!/usr/bin/env bash
#
# Aquilia Serializer Benchmark Runner
# ====================================
# Runs the full benchmark suite and saves results.
#
# Usage:
#   ./serializer_bench/run_bench_local.sh                  # full suite
#   ./serializer_bench/run_bench_local.sh --profile        # + py-spy flamegraph
#   ./serializer_bench/run_bench_local.sh --quick           # reduced iterations
#
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-env/bin/python}"
BENCH_SCRIPT="serializer_bench/bench_serializers.py"
RESULTS_DIR="serializer_bench/results"
FLAMEGRAPH_DIR="serializer_bench/flamegraphs"

mkdir -p "$RESULTS_DIR" "$FLAMEGRAPH_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULT_FILE="$RESULTS_DIR/bench_${TIMESTAMP}.json"

echo "=============================================="
echo "  Aquilia Serializer Benchmark"
echo "=============================================="
echo "  Python:    $($PYTHON --version 2>&1)"
echo "  Timestamp: $TIMESTAMP"
echo "=============================================="
echo ""

# Run benchmarks
echo "▸ Running benchmarks..."
$PYTHON "$BENCH_SCRIPT" 2>&1 | tee "$RESULTS_DIR/bench_${TIMESTAMP}.log"

# Copy the JSON results
if [ -f "serializer_bench/bench_results.json" ]; then
    cp "serializer_bench/bench_results.json" "$RESULT_FILE"
    echo ""
    echo "▸ Results saved to: $RESULT_FILE"
fi

# Optional profiling with py-spy
if [[ "${1:-}" == "--profile" ]]; then
    echo ""
    echo "▸ Running py-spy profiling..."

    if ! command -v py-spy &>/dev/null; then
        echo "  py-spy not found. Install with: pip install py-spy"
        echo "  Trying to install..."
        $PYTHON -m pip install py-spy 2>/dev/null || {
            echo "  Could not install py-spy. Skipping profiling."
            exit 0
        }
    fi

    SVG_FILE="$FLAMEGRAPH_DIR/flamegraph_${TIMESTAMP}.svg"
    echo "  Generating flamegraph → $SVG_FILE"
    py-spy record \
        --output "$SVG_FILE" \
        --format speedscope \
        --rate 1000 \
        -- $PYTHON "$BENCH_SCRIPT" >/dev/null 2>&1 || {
            echo "  py-spy failed (may need sudo on macOS). Trying with sudo..."
            sudo py-spy record \
                --output "$SVG_FILE" \
                --format speedscope \
                --rate 1000 \
                -- $PYTHON "$BENCH_SCRIPT" >/dev/null 2>&1 || {
                    echo "  Profiling failed. Skipping."
                }
        }

    if [ -f "$SVG_FILE" ]; then
        echo "  Flamegraph saved to: $SVG_FILE"
    fi
fi

# Summary comparison (if previous results exist)
PREV_RESULTS=$(ls -t "$RESULTS_DIR"/bench_*.json 2>/dev/null | head -2 | tail -1)
if [ -n "$PREV_RESULTS" ] && [ "$PREV_RESULTS" != "$RESULT_FILE" ]; then
    echo ""
    echo "▸ Previous result available for comparison:"
    echo "  Current:  $RESULT_FILE"
    echo "  Previous: $PREV_RESULTS"
    echo ""
    echo "  Compare with:"
    echo "    $PYTHON -c \"import json; a=json.load(open('$PREV_RESULTS')); b=json.load(open('$RESULT_FILE')); [print(f'  {k}: {a[k][\"median_ns\"]:>10,} → {b[k][\"median_ns\"]:>10,} ns') for k in b if k in a]\""
fi

echo ""
echo "Done."
