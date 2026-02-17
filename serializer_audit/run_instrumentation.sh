#!/usr/bin/env bash
#
# Serializer Instrumentation Runner
# ==================================
# Runs the instrumented serializer benchmarks and captures allocation data.
#
# Usage:
#   ./serializer_audit/run_instrumentation.sh
#   ./serializer_audit/run_instrumentation.sh --tracemalloc-top=20
#
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-env/bin/python}"
AUDIT_DIR="serializer_audit"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "=============================================="
echo "  Aquilia Serializer Instrumentation"
echo "=============================================="
echo "  Python:    $($PYTHON --version 2>&1)"
echo "  Timestamp: $TIMESTAMP"
echo "=============================================="
echo ""

TOP_N="${1:-20}"
TOP_N="${TOP_N#--tracemalloc-top=}"

# 1. Run tracemalloc profiling
echo "▸ Running tracemalloc allocation profiling..."
$PYTHON -c "
import tracemalloc
import sys
sys.path.insert(0, '.')

tracemalloc.start(25)  # 25 frames deep

from aquilia.serializers import Serializer, ListSerializer
from aquilia.serializers.fields import CharField, IntegerField, EmailField, FloatField

class ProfileSerializer(Serializer):
    name = CharField()
    email = EmailField()
    age = IntegerField()
    score = FloatField()

class Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)

# Warm up
s = ProfileSerializer(data={'name': 'x', 'email': 'x@x.com', 'age': 1, 'score': 1.0})
s.is_valid()

snap1 = tracemalloc.take_snapshot()

# Run 1000 serialization cycles
for i in range(1000):
    obj = Obj(name=f'user_{i}', email=f'u{i}@test.com', age=25, score=95.5)
    s = ProfileSerializer(instance=obj)
    _ = s.data

snap2 = tracemalloc.take_snapshot()

stats = snap2.compare_to(snap1, 'lineno')
print()
print(f'Top {int(\"$TOP_N\")} allocation hotspots (after 1000 serializations):')
print('=' * 80)
for stat in stats[:int('$TOP_N')]:
    print(stat)

print()
print('Summary:')
total_new = sum(s.size_diff for s in stats if s.size_diff > 0)
total_blocks = sum(s.count_diff for s in stats if s.count_diff > 0)
print(f'  Total new allocations:  {total_new:,} bytes')
print(f'  Total new blocks:       {total_blocks:,}')
print(f'  Per serialization:      {total_new // 1000:,} bytes')
" 2>&1 | tee "$AUDIT_DIR/tracemalloc_${TIMESTAMP}.log"

echo ""

# 2. Run validation profiling
echo "▸ Running validation path profiling..."
$PYTHON -c "
import tracemalloc
import sys
sys.path.insert(0, '.')

tracemalloc.start(25)

from aquilia.serializers import Serializer
from aquilia.serializers.fields import CharField, IntegerField, EmailField

class ValidateSerializer(Serializer):
    name = CharField(max_length=100)
    email = EmailField()
    age = IntegerField(min_value=0, max_value=150)

snap1 = tracemalloc.take_snapshot()

for i in range(1000):
    s = ValidateSerializer(data={
        'name': f'User {i}',
        'email': f'user{i}@example.com',
        'age': 25 + (i % 50)
    })
    s.is_valid()
    _ = s.validated_data

snap2 = tracemalloc.take_snapshot()

stats = snap2.compare_to(snap1, 'lineno')
print('Top 10 validation allocation hotspots:')
print('=' * 80)
for stat in stats[:10]:
    print(stat)
total_new = sum(s.size_diff for s in stats if s.size_diff > 0)
print(f'  Per validation: {total_new // 1000:,} bytes')
" 2>&1 | tee -a "$AUDIT_DIR/tracemalloc_${TIMESTAMP}.log"

echo ""

# 3. Generate the DOT graph as SVG if graphviz is available
if command -v dot &>/dev/null; then
    echo "▸ Rendering serializer_graph.dot → serializer_graph.svg"
    dot -Tsvg "$AUDIT_DIR/serializer_graph.dot" -o "$AUDIT_DIR/serializer_graph.svg"
    echo "  → $AUDIT_DIR/serializer_graph.svg"
else
    echo "▸ Graphviz not found. Install with: brew install graphviz"
    echo "  Then run: dot -Tsvg $AUDIT_DIR/serializer_graph.dot -o $AUDIT_DIR/serializer_graph.svg"
fi

echo ""
echo "Done. Full log: $AUDIT_DIR/tracemalloc_${TIMESTAMP}.log"
