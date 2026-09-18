#!/usr/bin/env bash
# Run BM25 retrieval eval locally and save results to a timestamped Markdown file.
# Each run produces its own file; nothing is overwritten.
#
# Usage: ./evaluation/run_eval_local.sh [--docs-path PATH] [--k K]
#
# Defaults: --docs-path <doc_indexer>/data  --k 10

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOC_INDEXER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_DIR="$(cd "$DOC_INDEXER_DIR/.." && pwd)"
RESULTS_DIR="$SCRIPT_DIR/results"
TIMESTAMP="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
RESULT_MD="$RESULTS_DIR/$TIMESTAMP.md"
RESULT_JSON="$RESULTS_DIR/$TIMESTAMP.json"

DOCS_PATH="${DOCS_PATH:-$DOC_INDEXER_DIR/data}"
K="${K:-10}"

# Parse optional args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --docs-path) DOCS_PATH="$2"; shift 2 ;;
        --k) K="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

mkdir -p "$RESULTS_DIR"

echo "=== BM25 retrieval eval ==="
echo "docs-path : $DOCS_PATH"
echo "k         : $K"
echo "result    : $RESULT_MD"
echo ""

cd "$APP_DIR"

# Capture output and write to Markdown file
{
    echo "# BM25 retrieval eval -- $TIMESTAMP"
    echo ""
    echo "- docs-path: \`$DOCS_PATH\`"
    echo "- k: $K"
    echo ""
    echo "## Results"
    echo ""
    PYTHONPATH="src:$DOC_INDEXER_DIR/src" poetry run python "$SCRIPT_DIR/run_retrieval_eval.py" \
        --mode bm25 \
        --docs-path "$DOCS_PATH" \
        --k "$K" \
        --queries "$SCRIPT_DIR/queries.jsonl" \
        --out "$RESULT_JSON"
} | tee "$RESULT_MD"

echo ""
echo "Saved: $RESULT_MD"
