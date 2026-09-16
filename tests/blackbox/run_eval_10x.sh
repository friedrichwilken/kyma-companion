#!/usr/bin/env bash
# Run the A2A evaluation 10 times against the locally-running app server.
# Each run produces three files in eval_results/:
#   run-N-<timestamp>.log             — full eval client output (scores, answers, expectations)
#   run-N-<timestamp>.server.log      — app server output (JSON log lines, includes doc_search events)
#   run-N-<timestamp>.doc_search.json — extracted doc_search log entries for this run
#   run-N-<timestamp>.metrics.json    — structured metrics report
#
# Uses the pre-built docs artifact at doc_indexer/artifact/ (checked into the repo).
# The app server is started/stopped for every run with a clean state.
#
# Usage:
#   cd tests/blackbox
#   bash run_eval_10x.sh
#
# Requirements:
#   - config/config.json in the repo root (copied from main worktree if missing)
#   - docker redis-local running  (or REDIS_URL set in env)
#   - poetry install done in the repo root AND in tests/blackbox/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RESULTS_DIR="$SCRIPT_DIR/eval_results"
CONFIG_JSON="$REPO_ROOT/config/config.json"
MAIN_CONFIG_JSON="/Users/I549741/claude/kyma/kyma-companion/main/config/config.json"
# Use the artifact already checked in under doc_indexer/artifact/ (DOCS_PATH overrides if set)
DOCS_ARTIFACT="${DOCS_PATH:-$REPO_ROOT/doc_indexer/artifact}"

mkdir -p "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# Ensure config.json is present
# ---------------------------------------------------------------------------

if [[ ! -f "$CONFIG_JSON" ]]; then
    if [[ -f "$MAIN_CONFIG_JSON" ]]; then
        echo "=== Copying config.json from main worktree ==="
        cp "$MAIN_CONFIG_JSON" "$CONFIG_JSON"
    else
        echo "ERROR: $CONFIG_JSON not found and $MAIN_CONFIG_JSON not available." >&2
        exit 1
    fi
fi

MAIN_CONFIG_DIR="$(dirname "$MAIN_CONFIG_JSON")"
CONFIG_DIR="$(dirname "$CONFIG_JSON")"
for f in encryption_key.pem resource_relations.json api_resources.json; do
    if [[ ! -f "$CONFIG_DIR/$f" ]] && [[ -f "$MAIN_CONFIG_DIR/$f" ]]; then
        echo "=== Copying $f from main worktree ==="
        cp "$MAIN_CONFIG_DIR/$f" "$CONFIG_DIR/$f"
    fi
done

# ---------------------------------------------------------------------------
# Validate docs artifact
# ---------------------------------------------------------------------------

if [[ ! -d "$DOCS_ARTIFACT" ]]; then
    echo "ERROR: docs artifact not found at $DOCS_ARTIFACT" >&2
    echo "  Set DOCS_PATH to an existing artifact directory, or run:" >&2
    echo "  pinakes resolve  (inside doc_indexer/)" >&2
    exit 1
fi
echo "=== Using docs artifact at $DOCS_ARTIFACT ==="

# ---------------------------------------------------------------------------
# Helper: start the app server, write logs to server_log, return PID
# ---------------------------------------------------------------------------

start_server() {
    local server_log="$1"
    (
        cd "$REPO_ROOT"
        PYTHONUNBUFFERED=1 LOG_FORMAT=json DOCS_PATH="$DOCS_ARTIFACT" CONFIG_PATH="$CONFIG_JSON" \
            poetry run fastapi run src/main.py --port 8000
    ) > "$server_log" 2>&1 &
    echo $!
}

# ---------------------------------------------------------------------------
# Helper: wait until /healthz is responding
# ---------------------------------------------------------------------------

wait_for_server() {
    local max_wait=120
    local elapsed=0
    while [[ $elapsed -lt $max_wait ]]; do
        if curl -sf http://localhost:8000/healthz > /dev/null 2>&1; then
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    echo "ERROR: server did not become ready within ${max_wait}s" >&2
    return 1
}

# ---------------------------------------------------------------------------
# Helper: extract doc_search entries from a JSON-format server log
# ---------------------------------------------------------------------------

extract_doc_search() {
    local server_log="$1"
    local out_json="$2"
    python3 - "$server_log" "$out_json" <<'PYEOF'
import json, sys

server_log_path = sys.argv[1]
out_path = sys.argv[2]
entries = []

with open(server_log_path) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        # search.py logs: logger.info("doc_search", extra={"query": ..., "results": [...]})
        # LOG_FORMAT=json serialises extra fields as top-level keys
        if obj.get("message") == "doc_search":
            entries.append({
                "query": obj.get("query", ""),
                "module_filter": obj.get("module_filter", ""),
                "result_count": obj.get("result_count", 0),
                "results": obj.get("results", []),
            })

with open(out_path, "w") as f:
    json.dump(entries, f, indent=2)

print(f"  Extracted {len(entries)} doc_search entries -> {out_path}")
PYEOF
}

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

cd "$SCRIPT_DIR"

for i in $(seq 1 10); do
    TIMESTAMP="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
    EVAL_LOG="$RESULTS_DIR/run-${i}-${TIMESTAMP}.log"
    SERVER_LOG="$RESULTS_DIR/run-${i}-${TIMESTAMP}.server.log"
    DOC_SEARCH_JSON="$RESULTS_DIR/run-${i}-${TIMESTAMP}.doc_search.json"
    METRICS_JSON="$RESULTS_DIR/run-${i}-${TIMESTAMP}.metrics.json"

    echo ""
    echo "========================================================================"
    echo "=== Run $i/10 starting at $TIMESTAMP"
    echo "========================================================================"

    echo "=== Starting app server (log -> $(basename "$SERVER_LOG")) ==="
    SERVER_PID=$(start_server "$SERVER_LOG")
    echo "=== Server PID: $SERVER_PID ==="

    if ! wait_for_server; then
        echo "ERROR: server failed to start for run $i — check $SERVER_LOG" >&2
        kill "$SERVER_PID" 2>/dev/null || true
        continue
    fi
    echo "=== Server ready ==="

    echo "=== Running eval (log -> $(basename "$EVAL_LOG")) ==="
    METRICS_REPORT_PATH="$METRICS_JSON" \
        poetry run python src/run_a2a_evaluation.py > "$EVAL_LOG" 2>&1 || true

    echo "=== Stopping server (PID $SERVER_PID) ==="
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true

    echo "=== Extracting doc_search entries ==="
    extract_doc_search "$SERVER_LOG" "$DOC_SEARCH_JSON"

    SCORE=$(grep "Overall success score" "$EVAL_LOG" | grep -oE '[0-9]+\.[0-9]+%' || echo "N/A")
    echo "=== Run $i/10 done -- score: $SCORE ==="

    if [[ "$i" -lt 10 ]]; then
        echo "=== Waiting 15 minutes before next run ==="
        sleep 900
    fi
done

# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------

echo ""
echo "========================================================================"
echo "=== All 10 runs complete. Results in: $RESULTS_DIR"
echo "========================================================================"
echo ""
printf "%-12s  %-10s  %s\n" "Run" "Score" "doc_search_calls"
for f in "$RESULTS_DIR"/run-*.log; do
    [[ "$f" == *.server.log ]] && continue
    RUN=$(basename "$f" | grep -oE 'run-[0-9]+')
    SCORE=$(grep "Overall success score" "$f" | grep -oE '[0-9]+\.[0-9]+%' || echo "N/A")
    DS_FILE="${f%.log}.doc_search.json"
    DOC_COUNT=$(python3 -c "import json; print(len(json.load(open('$DS_FILE'))))" 2>/dev/null || echo "?")
    printf "%-12s  %-10s  %s\n" "$RUN" "$SCORE" "$DOC_COUNT"
done
