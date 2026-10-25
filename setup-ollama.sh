#!/usr/bin/env bash

set -Eeuo pipefail

# ============================================================
# Configuration
# ============================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose-ollama.yml}"
OLLAMA_HOST_PORT="${OLLAMA_HOST_PORT:-11434}"

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
        END {
            if (!found) {
                print key "=" value
            }
        }
    ' .env > "$temp_file"

    mv "$temp_file" .env
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

command -v curl >/dev/null 2>&1 ||
    fail "curl is required."

command -v uv >/dev/null 2>&1 ||
    fail "uv is required. Install it from https://docs.astral.sh/uv/"

[[ -f "$COMPOSE_FILE" ]] ||
    fail "Missing $COMPOSE_FILE. Run this script from the project checkout."

# ============================================================
# 2. Initialize .env
# ============================================================

if [[ ! -f .env ]]; then
    [[ -f example.env ]] || fail "Missing example.env."
    cp example.env .env
    chmod 600 .env
fi

OLLAMA_CHAT_MODEL="${OLLAMA_CHAT_MODEL:-qwen2.5:0.5b}"
OLLAMA_EMBEDDING_MODEL="${OLLAMA_EMBEDDING_MODEL:-Qwen3-Embedding:0.6b}"
OLLAMA_GUARD_MODEL="${OLLAMA_GUARD_MODEL:-sileader/qwen3guard:0.6b}"
OLLAMA_PULL_MODELS="${OLLAMA_PULL_MODELS:-true}"

log "Writing Ollama container settings to .env."
set_env OLLAMA_CHAT_MODEL "$OLLAMA_CHAT_MODEL"
set_env OLLAMA_EMBEDDING_MODEL "$OLLAMA_EMBEDDING_MODEL"
set_env OLLAMA_GUARD_MODEL "$OLLAMA_GUARD_MODEL"
set_env OLLAMA_PULL_MODELS "$OLLAMA_PULL_MODELS"
set_env OLLAMA_HOST_PORT "$OLLAMA_HOST_PORT"
set_env CHATBOT_MODEL "$OLLAMA_CHAT_MODEL"
# Host-side scripts reach the published Ollama port. The
# Compose file rewrites this to http://ollama for rag-app.
set_env CHATBOT_SERVER "http://localhost"
set_env CHATBOT_SERVER_PORT "$OLLAMA_HOST_PORT"
set_env CHATBOT_API_KEY "ollama"
set_env EMBEDDING_MODEL "$OLLAMA_EMBEDDING_MODEL"
set_env EMBEDDING_MODEL_SERVER "http://localhost"
set_env EMBEDDING_MODEL_SERVER_PORT "$OLLAMA_HOST_PORT"
set_env EMBEDDING_MODEL_API_KEY "ollama"
set_env EMBEDDING_CHECK_CTX_LENGTH "false"
set_env GUARD_MODEL "$OLLAMA_GUARD_MODEL"
set_env GUARD_MODEL_SERVER "http://localhost"
set_env GUARD_MODEL_SERVER_PORT "$OLLAMA_HOST_PORT"
set_env GUARD_MODEL_API_KEY "ollama"
set_env QDRANT_COLLECTION "Egyptian_Civil_Law_131"
chmod 600 .env

# ============================================================
# 3. Start the Ollama container
# ============================================================

# Refuse to continue when a host Ollama instance already owns
# the published port. The container cannot bind it otherwise.
if curl -fsS "http://localhost:${OLLAMA_HOST_PORT}/api/version" \
    >/dev/null 2>&1; then
    if ! docker ps --format '{{.Names}}' | grep -qx "ollama"; then
        fail "Port ${OLLAMA_HOST_PORT} is already used by another Ollama instance (host Ollama). Stop it with 'sudo systemctl stop ollama' and rerun this script, or set OLLAMA_HOST_PORT to a free port."
    fi
fi

log "Starting the Ollama container."
docker compose -f "$COMPOSE_FILE" up -d ollama

log "Waiting for the Ollama container to become ready..."
OLLAMA_WAIT_SECONDS="${OLLAMA_WAIT_SECONDS:-300}"
deadline=$((SECONDS + OLLAMA_WAIT_SECONDS))

until docker compose -f "$COMPOSE_FILE" exec -T ollama \
    ollama list >/dev/null 2>&1; do
    if (( SECONDS >= deadline )); then
        docker compose -f "$COMPOSE_FILE" logs --tail=80 ollama
        fail "Ollama did not become ready within ${OLLAMA_WAIT_SECONDS}s."
    fi

    sleep 2
done

log "Ollama container is ready."

# ============================================================
# 4. Pull the required models into the Ollama volume
# ============================================================

if [[ "$OLLAMA_PULL_MODELS" == "true" ]]; then
    for model in \
        "$OLLAMA_CHAT_MODEL" \
        "$OLLAMA_EMBEDDING_MODEL" \
        "$OLLAMA_GUARD_MODEL"; do
        if docker compose -f "$COMPOSE_FILE" exec -T ollama \
            ollama show "$model" >/dev/null 2>&1; then
            log "Ollama model already available: $model"
        else
            log "Pulling Ollama model: $model"
            docker compose -f "$COMPOSE_FILE" exec -T ollama \
                ollama pull "$model"
        fi
    done
else
    log "Skipping model pulls because OLLAMA_PULL_MODELS is not true."
fi

# ============================================================
# 5. Run the shared setup workflow
# ============================================================

export INFERENCE_BACKEND=ollama
export COMPOSE_FILE
export EMBEDDING_HEALTH_URL="http://localhost:${OLLAMA_HOST_PORT}/v1/models"
export INGESTION_EMBEDDING_SERVER=http://localhost
export INGESTION_EMBEDDING_PORT="$OLLAMA_HOST_PORT"
export INGESTION_EMBEDDING_MODEL="$OLLAMA_EMBEDDING_MODEL"
export INGESTION_CHECK_CTX_LENGTH=false

exec ./setup.sh
