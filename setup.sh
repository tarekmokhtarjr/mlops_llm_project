
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

DVC_CONFIG=".dvc/config"

QDRANT_URL="http://localhost:6333"
EMBEDDING_URL="http://localhost:8001/v1/models"

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

command -v git >/dev/null 2>&1 ||
    fail "Git is required."

[[ -f "$COMPOSE_FILE" ]] ||
    fail "Missing $COMPOSE_FILE. Run this script from the project checkout."

# ============================================================
# 2. Initialize .env
# ============================================================

if [[ -f ".env" ]]; then
    log ".env already exists; preserving the existing configuration."
else
    log "Creating .env from dev/example.env."

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
# 3. Validate the Google Drive DVC remote
# ============================================================

[[ -f "$DVC_CONFIG" ]] ||
    fail "Missing $DVC_CONFIG. Configure the Google Drive DVC remote first."

grep -Fq 'remote = gdrive' "$DVC_CONFIG" ||
    fail "The DVC configuration must define 'remote = gdrive'."

grep -Fq 'gdrive_acknowledge_abuse = true' "$DVC_CONFIG" ||
    fail "Expected gdrive_acknowledge_abuse = true in $DVC_CONFIG."

grep -Eq '^[[:space:]]*gdrive_client_id[[:space:]]*=' "$DVC_CONFIG" ||
    fail "Missing gdrive_client_id in $DVC_CONFIG."

grep -Eq '^[[:space:]]*gdrive_client_secret[[:space:]]*=' "$DVC_CONFIG" ||
    fail "Missing gdrive_client_secret in $DVC_CONFIG."

if grep -Fq '<place-client-id-here>' "$DVC_CONFIG" ||
   grep -Fq '<place-client-secret-here>' "$DVC_CONFIG"; then
    fail "Replace the Google OAuth client ID and client secret placeholders in .dvc/config before continuing."
fi

log "Google Drive DVC configuration looks valid."

# ============================================================
# 4. Pull the dataset using DVC
# ============================================================

log "Pulling the dataset from the configured Google Drive remote."

# DVC and its Google Drive support are installed in a temporary
# uv tool environment, without adding DVC to project dependencies.
uv tool run --from 'dvc[gdrive]' dvc pull

[[ -s "$HTML_FILE" ]] ||
    fail "DVC pull did not produce $HTML_FILE. Check the DVC remote, credentials, and dataset tracking."

log "Source HTML is available."

# ============================================================
# 5. Build the application image
# ============================================================

log "Building the rag-app Docker image."

docker compose -f "$COMPOSE_FILE" build rag-app

# ============================================================
# 6. Install project dependencies on the host
# ============================================================

log "Synchronizing Python dependencies."

uv sync --no-dev

# ============================================================
# 7. Start Qdrant and the embedding model
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
            docker compose -f "$COMPOSE_FILE" logs --tail=80 qdrant embedding
            fail "$description did not become ready within ${MAX_WAIT_SECONDS}s."
        fi

        sleep 5
    done

    log "$description is responding."
}

wait_for_url "$QDRANT_URL/healthz" "Qdrant"
wait_for_url "$EMBEDDING_URL" "Embedding model API"

# ============================================================
# 8. Extract Egyptian laws from HTML into JSON
# ============================================================

log "Extracting Egyptian laws from HTML."

uv run --no-sync python src/app/extract_egyptian_laws.py

[[ -s "$JSON_FILE" ]] ||
    fail "Extraction did not produce $JSON_FILE."

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
# 9. Embed and store the laws in Qdrant
# ============================================================

log "Embedding laws and storing them in Qdrant."

uv run --no-sync python src/app/embed_and_store_data.py

# ============================================================
# 10. Finish
# ============================================================

log "Setup completed successfully."
log "Qdrant dashboard: $QDRANT_URL/dashboard"
log "Embedding API: http://localhost:8001"
log "Application image has been built."
log "Only Qdrant and the embedding service were started."
