#!/usr/bin/env bash

set -Eeuo pipefail

# Run from any directory; paths are resolved relative to the repository.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DATASET="src/app/evaluation/dataset/civil_code_eval_ollama.json"
OUTPUT_DIR="evaluation/results/ollama"
MLFLOW_HOST="127.0.0.1"
MLFLOW_PORT="${MLFLOW_PORT:-5000}"
MLFLOW_TRACKING_URI="http://${MLFLOW_HOST}:${MLFLOW_PORT}"
MLFLOW_DB="$ROOT_DIR/mlflow-ollama.db"
MLFLOW_ARTIFACTS="$ROOT_DIR/mlartifacts-ollama"
LOG_DIR="$ROOT_DIR/logs"
MLFLOW_LOG="$LOG_DIR/mlflow-ollama.log"
TOP_K="${TOP_K:-10}"
EVAL_LIMIT="${EVAL_LIMIT:-0}"

MLFLOW_PID=""
STARTED_MLFLOW="false"

log() {
    printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

fail() {
    printf '\nERROR: %s\n' "$*" >&2
    exit 1
}

cleanup_on_failure() {
    local status=$?

    if [[ "$status" -ne 0 && "$STARTED_MLFLOW" == "true" ]]; then
        log "Evaluation failed. Stopping the MLflow server started by this script."
        if [[ -n "$MLFLOW_PID" ]]; then
            kill "$MLFLOW_PID" 2>/dev/null || true
        fi
        log "MLflow server log: $MLFLOW_LOG"
    fi

    # On success, leave MLflow running for inspection in the browser.
    exit "$status"
}
trap cleanup_on_failure EXIT

require_command() {
    command -v "$1" >/dev/null 2>&1 ||
        fail "Required command not found: $1"
}

wait_for_url() {
    local url="$1"
    local description="$2"
    local attempts="${3:-60}"

    log "Waiting for ${description}..."

    for ((i = 1; i <= attempts; i++)); do
        if curl --connect-timeout 2 -fsS "$url" >/dev/null 2>&1; then
            log "${description} is responding."
            return 0
        fi
        sleep 2
    done

    fail "Timed out waiting for ${description} at ${url}"
}

require_command curl
require_command uv
require_command docker

[[ -f ".env" ]] ||
    fail "Missing .env. Run ./setup-ollama.sh first."

[[ -f "$DATASET" ]] ||
    fail "Dataset not found: $DATASET"

mkdir -p "$OUTPUT_DIR" "$LOG_DIR" "$MLFLOW_ARTIFACTS"

# Make host-side evaluation use published ports, not Docker service names.
export QDRANT_URL="http://127.0.0.1:6333"
export QDRANT_HOST="127.0.0.1"
export QDRANT_PORT="6333"

# setup-ollama.sh configures these model names and ports in .env.
# load_dotenv() in run_ragas.py will load the model names from that file.
export CHATBOT_SERVER="http://127.0.0.1"
export CHATBOT_SERVER_PORT="11434"
export EMBEDDING_MODEL_SERVER="http://127.0.0.1"
export EMBEDDING_MODEL_SERVER_PORT="11434"
export GUARD_MODEL_SERVER="http://127.0.0.1"
export GUARD_MODEL_SERVER_PORT="11434"

# The 0.5B chat model is too weak for RAGAS structured-output metrics and
# can loop until it hits max_tokens. Use a stronger model for the judge.
export RAGAS_JUDGE_MODEL="${RAGAS_JUDGE_MODEL:-qwen2.5:1.5b}"

# Langfuse is not part of the Ollama Compose stack. Disable tracing by
# default so evaluation does not stall on unreachable Langfuse exports.
export LANGFUSE_ENABLED="${LANGFUSE_ENABLED:-false}"

export MLFLOW_TRACKING_URI
export MLFLOW_EXPERIMENT_NAME="egyptian-civil-code-rag-ollama-evaluation"

log "Checking Docker services..."
docker compose -f docker-compose-ollama.yml ps

log "Checking Qdrant..."
wait_for_url "http://127.0.0.1:6333/collections" "Qdrant" 30

log "Checking Ollama..."
wait_for_url "http://127.0.0.1:11434/api/version" "Ollama" 30
wait_for_url "http://127.0.0.1:11434/v1/models" "Ollama OpenAI-compatible API" 30

log "Checking RAGAS judge model: $RAGAS_JUDGE_MODEL"
if ! docker compose -f docker-compose-ollama.yml exec -T ollama \
    ollama show "$RAGAS_JUDGE_MODEL" >/dev/null 2>&1; then
    log "Pulling RAGAS judge model: $RAGAS_JUDGE_MODEL"
    docker compose -f docker-compose-ollama.yml exec -T ollama \
        ollama pull "$RAGAS_JUDGE_MODEL"
fi

# Start MLflow only if there is not already a responding server.
if curl --connect-timeout 2 -fsS \
    "$MLFLOW_TRACKING_URI/health" >/dev/null 2>&1; then
    log "Reusing existing MLflow server at $MLFLOW_TRACKING_URI"
else
    log "Starting MLflow server on port $MLFLOW_PORT..."

    uv run mlflow server \
        --host "$MLFLOW_HOST" \
        --port "$MLFLOW_PORT" \
        --backend-store-uri "sqlite:///$MLFLOW_DB" \
        --default-artifact-root "$MLFLOW_ARTIFACTS" \
        >"$MLFLOW_LOG" 2>&1 &

    MLFLOW_PID=$!
    STARTED_MLFLOW="true"

    # Give MLflow time to start. On failure, the EXIT trap cleans it up.
    wait_for_url "$MLFLOW_TRACKING_URI/health" "MLflow" 60
fi

log "Running RAGAS evaluation..."
log "Dataset: $DATASET"
log "Top-k: $TOP_K"
log "Case limit: ${EVAL_LIMIT} (0 means all cases)"
log "Judge model: $RAGAS_JUDGE_MODEL"
log "Langfuse tracing: $LANGFUSE_ENABLED"

EVAL_ARGS=(
    --dataset "$DATASET"
    --output-dir "$OUTPUT_DIR"
    --top-k "$TOP_K"
)

if [[ "$EVAL_LIMIT" != "0" ]]; then
    EVAL_ARGS+=(--limit "$EVAL_LIMIT")
fi

uv run python src/app/evaluation/run_ragas.py "${EVAL_ARGS[@]}"

log "Evaluation finished."
log "MLflow UI: $MLFLOW_TRACKING_URI"
log "MLflow experiment: $MLFLOW_EXPERIMENT_NAME"
log "Detailed results: $OUTPUT_DIR/results.json"
log "Summary: $OUTPUT_DIR/summary.json"

if [[ "$STARTED_MLFLOW" == "true" ]]; then
    log "MLflow remains running. Stop it later with:"
    log "  kill $MLFLOW_PID"
    log "MLflow server log: $MLFLOW_LOG"
fi
