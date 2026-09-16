#!/usr/bin/env bash
# Run the A2A evaluation test 10 times and save each result to a timestamped file.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESULTS_DIR="$SCRIPT_DIR/eval_results"
mkdir -p "$RESULTS_DIR"

cd "$SCRIPT_DIR"

for i in $(seq 1 10); do
    TIMESTAMP="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
    OUT="$RESULTS_DIR/run-${i}-${TIMESTAMP}.log"
    echo "=== Run $i/10 starting at $TIMESTAMP ==="
    poetry run python src/run_a2a_evaluation.py > "$OUT" 2>&1 || true
    SCORE=$(grep "Overall success score" "$OUT" | grep -oE '[0-9]+\.[0-9]+%' || echo "N/A")
    echo "=== Run $i/10 done -- score: $SCORE (saved to $OUT) ==="
    if [ "$i" -lt 10 ]; then
        echo "=== Waiting 15 minutes before next run ==="
        sleep 900
    fi
done

echo ""
echo "=== All 10 runs complete. Scores: ==="
for f in "$RESULTS_DIR"/run-*.log; do
    RUN=$(basename "$f" | grep -oE 'run-[0-9]+')
    SCORE=$(grep "Overall success score" "$f" | grep -oE '[0-9]+\.[0-9]+%' || echo "N/A")
    echo "  $RUN: $SCORE"
done
