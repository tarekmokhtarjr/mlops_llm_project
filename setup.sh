#!/usr/bin/env bash

set -Eeuo pipefail

# ============================================================
# Configuration
# ============================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

INFERENCE_BACKEND="${INFERENCE_BACKEND:-vllm}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose-dev.yml}"

HTML_FILE="data/egyptian_civil_law_131_1948.html"
JSON_FILE="data/egyptian_civil_law_131_1948.json"

QDRANT_URL="http://localhost:6333"
EMBEDDING_HEALTH_URL="${EMBEDDING_HEALTH_URL:-http://localhost:8001/v1/models}"
INGESTION_EMBEDDING_SERVER="${INGESTION_EMBEDDING_SERVER:-http://localhost}"
INGESTION_EMBEDDING_PORT="${INGESTION_EMBEDDING_PORT:-8001}"
INGESTION_EMBEDDING_MODEL="${INGESTION_EMBEDDING_MODEL:-Qwen/Qwen3-Embedding-0.6B}"
INGESTION_CHECK_CTX_LENGTH="${INGESTION_CHECK_CTX_LENGTH:-true}"

MAX_WAIT_SECONDS="${MAX_WAIT_SECONDS:-900}"

# ============================================================
# Helpers
# ============================================================

log() {
    printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

fail() {
    printf '\nERROR: %s\n' "$*" >&2
    exit 1
}

set_env() {
    local key="$1"
    local value="$2"
    local temp_file
    temp_file="$(mktemp)"

    awk -v key="$key" -v value="$value" '
        BEGIN { found = 0 }
        index($0, key "=") == 1 {
            print key "=" value
            found = 1
            next
        }
        { print }
        END { if (!found) print key "=" value }
    ' .env > "$temp_file"

    mv "$temp_file" .env
}

wait_for_url() {
    local url="$1"
    local description="$2"
    local deadline=$((SECONDS + MAX_WAIT_SECONDS))

    log "Waiting for $description..."

    until curl -fsS "$url" >/dev/null 2>&1; do
        if (( SECONDS >= deadline )); then
            docker compose -f "$COMPOSE_FILE" ps
            docker compose -f "$COMPOSE_FILE" logs --tail=80 qdrant
            if [[ "$INFERENCE_BACKEND" == "ollama" ]]; then
                docker compose -f "$COMPOSE_FILE" logs --tail=80 ollama
            fi
            fail "$description did not become ready within ${MAX_WAIT_SECONDS}s."
        fi

        sleep 5
    done

    log "$description is responding."
}

# ============================================================
# 1. Check prerequisites
# ============================================================

command -v docker >/dev/null 2>&1 ||
    fail "Docker is not installed or is not on PATH."

docker info >/dev/null 2>&1 ||
    fail "Docker is not running or the current user lacks permission."

docker compose version >/dev/null 2>&1 ||
    fail "Docker Compose V2 is required."

command -v uv >/dev/null 2>&1 ||
    fail "uv is required. Install it from https://docs.astral.sh/uv/"

command -v curl >/dev/null 2>&1 ||
    fail "curl is required."

[[ -f "$COMPOSE_FILE" ]] ||
    fail "Missing $COMPOSE_FILE. Run this script from the project checkout."

# ============================================================
# 2. Initialize .env
# ============================================================

if [[ -f ".env" ]]; then
    log ".env already exists; preserving the existing configuration."
else
    [[ -f "example.env" ]] || fail "Missing example.env."
    log "Creating .env from example.env."
    cp example.env .env
    chmod 600 .env
fi

if [[ "$INFERENCE_BACKEND" == "vllm" ]]; then
    log "Writing vLLM development settings to .env."
    set_env CHATBOT_MODEL "${VLLM_CHAT_MODEL:-Qwen/Qwen2.5-0.5B-Instruct}"
    set_env CHATBOT_SERVER "http://llm"
    set_env CHATBOT_SERVER_PORT "8000"
    set_env CHATBOT_API_KEY "dumb"
    set_env EMBEDDING_MODEL "${VLLM_EMBEDDING_MODEL:-Qwen/Qwen3-Embedding-0.6B}"
    set_env EMBEDDING_MODEL_SERVER "http://embedding"
    set_env EMBEDDING_MODEL_SERVER_PORT "8000"
    set_env EMBEDDING_MODEL_API_KEY "dumb"
    set_env EMBEDDING_CHECK_CTX_LENGTH "true"
    set_env GUARD_MODEL "${VLLM_GUARD_MODEL:-Qwen/Qwen3Guard-Gen-0.6B}"
    set_env GUARD_MODEL_SERVER "http://llm_guard"
    set_env GUARD_MODEL_SERVER_PORT "8000"
    set_env GUARD_MODEL_API_KEY "dumb"
    set_env QDRANT_COLLECTION "Egyptian_Civil_Law_131"
    chmod 600 .env
fi

# ============================================================
# 3. Validate the local dataset
# ============================================================

[[ -s "$HTML_FILE" ]] ||
    fail "Missing or empty $HTML_FILE. Place the dataset in the data/ directory."

log "Using inference backend: $INFERENCE_BACKEND"
log "Using the existing local dataset: $HTML_FILE"

# ============================================================
# 4. Build the application image
# ============================================================

log "Building the rag-app Docker image."
docker compose -f "$COMPOSE_FILE" build rag-app

# ============================================================
# 5. Install project dependencies on the host
# ============================================================

log "Synchronizing Python dependencies."
uv sync --no-dev

# ============================================================
# 6. Start dependencies
# ============================================================

if [[ "$INFERENCE_BACKEND" == "vllm" ]]; then
    log "Starting Qdrant and the vLLM embedding service."
    docker compose -f "$COMPOSE_FILE" up -d qdrant embedding
else
    log "Starting Qdrant and the Ollama container."
    docker compose -f "$COMPOSE_FILE" up -d qdrant ollama
fi

wait_for_url "$QDRANT_URL/healthz" "Qdrant"
wait_for_url "$EMBEDDING_HEALTH_URL" "$INFERENCE_BACKEND embedding API"

# ============================================================
# 7. Extract Egyptian laws from HTML into JSON
# ============================================================

log "Extracting Egyptian laws from HTML."
uv run --no-sync python src/app/extract_egyptian_laws.py

[[ -s "$JSON_FILE" ]] || fail "Extraction did not produce $JSON_FILE."

uv run --no-sync python -c '
import json
from pathlib import Path

path = Path("data/egyptian_civil_law_131_1948.json")
records = json.loads(path.read_text(encoding="utf-8"))

if not isinstance(records, list) or not records:
    raise SystemExit(f"Expected a non-empty JSON list: {path}")

print(f"Validated {len(records)} extracted law records.")
'

# ============================================================
# 8. Embed and store the laws in Qdrant
# ============================================================

log "Embedding laws and storing them in Qdrant."
EMBEDDING_MODEL_SERVER="$INGESTION_EMBEDDING_SERVER" \
EMBEDDING_MODEL_SERVER_PORT="$INGESTION_EMBEDDING_PORT" \
EMBEDDING_MODEL="$INGESTION_EMBEDDING_MODEL" \
EMBEDDING_CHECK_CTX_LENGTH="$INGESTION_CHECK_CTX_LENGTH" \
uv run --no-sync python src/app/embed_and_store_data.py

# ============================================================
# 9. Finish
# ============================================================

log "Setup completed successfully."
log "Qdrant dashboard: $QDRANT_URL/dashboard"
log "Embedding API: $EMBEDDING_HEALTH_URL"
log "Application image has been built."
log "To start the complete stack, run:"
log "docker compose -f $COMPOSE_FILE up -d"
