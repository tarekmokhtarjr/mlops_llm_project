#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

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

command -v ollama >/dev/null 2>&1 ||
    fail "Ollama is required. Install it from https://ollama.com/download"

curl -fsS http://localhost:11434/api/version >/dev/null 2>&1 ||
    fail "Ollama is not reachable at http://localhost:11434. Start the Ollama application first."

if [[ ! -f .env ]]; then
    [[ -f example.env ]] || fail "Missing example.env."
    cp example.env .env
fi

OLLAMA_CHAT_MODEL="${OLLAMA_CHAT_MODEL:-qwen2.5:0.5b}"
OLLAMA_EMBEDDING_MODEL="${OLLAMA_EMBEDDING_MODEL:-Qwen3-Embedding:0.6b}"
OLLAMA_GUARD_MODEL="${OLLAMA_GUARD_MODEL:-sileader/qwen3guard:0.6b}"

log "Writing Ollama development settings to .env."
set_env OLLAMA_CHAT_MODEL "$OLLAMA_CHAT_MODEL"
set_env OLLAMA_EMBEDDING_MODEL "$OLLAMA_EMBEDDING_MODEL"
set_env OLLAMA_GUARD_MODEL "$OLLAMA_GUARD_MODEL"
set_env CHATBOT_MODEL "$OLLAMA_CHAT_MODEL"
set_env CHATBOT_SERVER "http://localhost"
set_env CHATBOT_SERVER_PORT "11434"
set_env CHATBOT_API_KEY "ollama"
set_env EMBEDDING_MODEL "$OLLAMA_EMBEDDING_MODEL"
set_env EMBEDDING_MODEL_SERVER "http://localhost"
set_env EMBEDDING_MODEL_SERVER_PORT "11434"
set_env EMBEDDING_MODEL_API_KEY "ollama"
set_env EMBEDDING_CHECK_CTX_LENGTH "false"
set_env GUARD_MODEL "$OLLAMA_GUARD_MODEL"
set_env GUARD_MODEL_SERVER "http://localhost"
set_env GUARD_MODEL_SERVER_PORT "11434"
set_env GUARD_MODEL_API_KEY "ollama"
set_env QDRANT_COLLECTION "Egyptian_Civil_Law_131"
chmod 600 .env

if [[ "${OLLAMA_PULL_MODELS:-true}" == "true" ]]; then
    for model in \
        "$OLLAMA_CHAT_MODEL" \
        "$OLLAMA_EMBEDDING_MODEL" \
        "$OLLAMA_GUARD_MODEL"; do
        if ollama show "$model" >/dev/null 2>&1; then
            log "Ollama model already available: $model"
        else
            log "Pulling Ollama model: $model"
            ollama pull "$model"
        fi
    done
fi

export INFERENCE_BACKEND=ollama
export COMPOSE_FILE=docker-compose-ollama.yml
export EMBEDDING_HEALTH_URL=http://localhost:11434/v1/models
export INGESTION_EMBEDDING_SERVER=http://localhost
export INGESTION_EMBEDDING_PORT=11434
export INGESTION_EMBEDDING_MODEL="$OLLAMA_EMBEDDING_MODEL"
export INGESTION_CHECK_CTX_LENGTH=false

exec ./setup.sh
