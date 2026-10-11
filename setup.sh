
#!/usr/bin/env bash

set -Eeuo pipefail

# ============================================================
# Configuration
# ============================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="docker-compose-dev.yml"

HTML_FILE="data/egyptian_civil_law_131_1948.html"
JSON_FILE="data/egyptian_civil_law_131_1948.json"
DVC_SERVICE_ACCOUNT="arabic-legal-documents-llm-9a9b19f505c4.json"

QDRANT_URL="http://localhost:6333"
EMBEDDING_URL="http://localhost:8001/v1/models"

MAX_WAIT_SECONDS=600

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

# ============================================================
# 1. Initialize .env
# ============================================================

if [[ -f ".env" ]]; then
    log ".env already exists; keeping the existing configuration."
else
    log "Creating .env from the dev branch example.env."

    # Prefer a locally available dev branch reference.
    if git show origin/dev:example.env > .env 2>/dev/null; then
        :
    elif curl -fsSL \
        "https://raw.githubusercontent.com/tarekmokhtarjr/mlops_llm_project/dev/example.env" \
        -o .env; then
        :
    else
        rm -f .env
        fail "Could not retrieve dev/example.env."
    fi

    chmod 600 .env
    log ".env created."
fi

# ============================================================
# 2. Validate DVC configuration and credentials
# ============================================================

[[ -f ".dvc/config" ]] ||
    fail "Missing .dvc/config. Restore your local Google Drive DVC configuration."

[[ -f "$DVC_SERVICE_ACCOUNT" ]] ||
    fail "Missing $DVC_SERVICE_ACCOUNT. Place your Google Drive service-account JSON in the repository root."

log "Pulling dataset from Google Drive using DVC."

# Install/use DVC with Google Drive support without adding
# DVC to the application's dependency environment.
uv tool run --from 'dvc[gdrive]' dvc pull

[[ -s "$HTML_FILE" ]] ||
    fail "DVC pull did not produce $HTML_FILE."

log "Source HTML is available."

# ============================================================
# 3. Build the application Docker image
# ============================================================

log "Building the application image."

docker compose -f "$COMPOSE_FILE" build rag-app

# ============================================================
# 4. Install project dependencies on the host
# ============================================================

log "Synchronizing Python dependencies."

uv sync --no-dev

# ============================================================
# 5. Start Qdrant and the embedding model
# ============================================================

log "Starting Qdrant and the embedding service."

docker compose -f "$COMPOSE_FILE" up -d qdrant embedding

wait_for_url() {
    local url="$1"
    local description="$2"
    local deadline=$((SECONDS + MAX_WAIT_SECONDS))

    log "Waiting for $description..."

    until curl -fsS "$url" >/dev/null 2>&1; do
        if (( SECONDS >= deadline )); then
            docker compose -f "$COMPOSE_FILE" ps
            docker compose -f "$COMPOSE_FILE" logs --tail=80 \
                qdrant embedding
            fail "$description did not become ready within ${MAX_WAIT_SECONDS}s."
        fi

        sleep 5
    done

    log "$description is responding."
}

wait_for_url "$QDRANT_URL/healthz" "Qdrant"
wait_for_url "$EMBEDDING_URL" "Embedding model API"

# ============================================================
# 6. Extract the Egyptian laws
# ============================================================

log "Extracting Egyptian laws from HTML."

uv run --no-sync python src/app/extract_egyptian_laws.py

[[ -s "$JSON_FILE" ]] ||
    fail "Extraction did not produce $JSON_FILE."

# Validate the JSON and ensure it contains records.
uv run --no-sync python -c '
import json
from pathlib import Path

path = Path("data/egyptian_civil_law_131_1948.json")
data = json.loads(path.read_text(encoding="utf-8"))

if not isinstance(data, list) or not data:
    raise SystemExit(f"Expected a non-empty JSON list: {path}")

print(f"Validated {len(data)} extracted law records.")
'

# ============================================================
# 7. Embed and store laws in Qdrant
# ============================================================

log "Embedding laws and storing them in Qdrant."

uv run --no-sync python src/app/embed_and_store_data.py

log "Setup completed successfully."
log "Qdrant dashboard: $QDRANT_URL/dashboard"
log "Embedding API: http://localhost:8001"
log "Application image has been built."
