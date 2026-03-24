#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# keepalive.sh — Prevent Render cold starts by pinging health endpoints
#
# Render Starter instances spin down after ~15 minutes of inactivity.
# This script sends lightweight HEAD requests to keep both services warm.
#
# Usage:
#   Run via Render Cron Job (every 10 minutes) or external scheduler.
#
#   # Manual test:
#   ./scripts/keepalive.sh
#
#   # With Render Cron Job (render.yaml):
#   Add a cron job entry — see render.yaml for configuration.
#
# Endpoints pinged:
#   - AI Identity API:     https://ai-identity-api.onrender.com/health
#   - AI Identity Gateway: https://ai-identity-gateway.onrender.com/health
# ──────────────────────────────────────────────────────────────────────

set -euo pipefail

API_URL="https://ai-identity-api.onrender.com/health"
GATEWAY_URL="https://ai-identity-gateway.onrender.com/health"
TIMEOUT=30

timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

ping_service() {
    local name="$1"
    local url="$2"

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --head \
        --max-time "$TIMEOUT" \
        "$url" 2>/dev/null) || http_code="000"

    if [[ "$http_code" == "200" ]]; then
        echo "$(timestamp) ✅ $name: healthy ($http_code)"
    else
        echo "$(timestamp) ⚠️  $name: responded $http_code (may be waking up)"
        # Retry once after a brief pause — service may be cold-starting
        sleep 5
        http_code=$(curl -s -o /dev/null -w "%{http_code}" \
            --head \
            --max-time "$TIMEOUT" \
            "$url" 2>/dev/null) || http_code="000"
        if [[ "$http_code" == "200" ]]; then
            echo "$(timestamp) ✅ $name: healthy after retry ($http_code)"
        else
            echo "$(timestamp) ❌ $name: unhealthy after retry ($http_code)"
        fi
    fi
}

echo "$(timestamp) 🔄 AI Identity keepalive ping starting..."
ping_service "API" "$API_URL"
ping_service "Gateway" "$GATEWAY_URL"
echo "$(timestamp) ✅ Keepalive complete."
