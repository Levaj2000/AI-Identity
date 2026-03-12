#!/usr/bin/env bash
# AI Identity — One-time Docker environment setup
# Generates .env from .env.example with real cryptographic keys.
#
# Usage:  make setup   (or: bash scripts/docker-setup.sh)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
ENV_EXAMPLE="$REPO_ROOT/.env.example"

# ── Colors ──────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo -e "${GREEN}AI Identity — Docker Setup${NC}"
echo "────────────────────────────────────────"

# ── Copy template ───────────────────────────────────────────────────────
if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠  .env already exists — skipping copy (delete it first to regenerate)${NC}"
else
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "✓  Copied .env.example → .env"
fi

# ── Generate security keys ─────────────────────────────────────────────
generate_fernet_key() {
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null \
        || openssl rand -base64 32
}

generate_urlsafe_key() {
    local bytes="${1:-64}"
    python3 -c "import secrets; print(secrets.token_urlsafe($bytes))" 2>/dev/null \
        || openssl rand -base64 "$bytes" | tr -d '=/+' | head -c "$bytes"
}

# Only fill in blank keys (don't overwrite existing values)
fill_key() {
    local key_name="$1"
    local key_value="$2"

    if grep -q "^${key_name}=$" "$ENV_FILE"; then
        # Key exists but is empty — fill it in
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^${key_name}=$|${key_name}=${key_value}|" "$ENV_FILE"
        else
            sed -i "s|^${key_name}=$|${key_name}=${key_value}|" "$ENV_FILE"
        fi
        echo "✓  Generated $key_name"
    else
        echo "·  $key_name already set"
    fi
}

fill_key "CREDENTIAL_ENCRYPTION_KEY" "$(generate_fernet_key)"
fill_key "INTERNAL_SERVICE_KEY" "$(generate_urlsafe_key 64)"

# Replace placeholder AUDIT_HMAC_KEY if it's still the default
if grep -q "^AUDIT_HMAC_KEY=dev-hmac-key-change-in-production$" "$ENV_FILE"; then
    AUDIT_KEY="$(generate_urlsafe_key 32)"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^AUDIT_HMAC_KEY=dev-hmac-key-change-in-production$|AUDIT_HMAC_KEY=${AUDIT_KEY}|" "$ENV_FILE"
    else
        sed -i "s|^AUDIT_HMAC_KEY=dev-hmac-key-change-in-production$|AUDIT_HMAC_KEY=${AUDIT_KEY}|" "$ENV_FILE"
    fi
    echo "✓  Generated AUDIT_HMAC_KEY"
else
    echo "·  AUDIT_HMAC_KEY already set"
fi

# ── Done ────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}Setup complete!${NC} Next steps:"
echo ""
echo "  make up       # Build and start all services"
echo "  make seed     # Seed sample agents and API keys"
echo "  make logs     # Tail service logs"
echo ""
echo "  API:     http://localhost:8001/docs"
echo "  Gateway: http://localhost:8002/docs"
echo ""
