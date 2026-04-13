#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# setup-uptimerobot.sh — Provision UptimeRobot monitors for AI Identity
#
# Prerequisites:
#   1. Create a free account at https://uptimerobot.com
#   2. Go to My Settings → API Settings → Create Main API Key
#   3. Set UPTIMEROBOT_API_KEY in your environment or .env
#
# Usage:
#   export UPTIMEROBOT_API_KEY="ur_your_key_here"
#   ./scripts/setup-uptimerobot.sh
#
# What it does:
#   - Creates HTTP(s) monitors for all production services
#   - Sets 5-minute check intervals (free tier)
#   - Adds your alert contact for email notifications
#   - Creates a public status page for design partners
# ──────────────────────────────────────────────────────────────────────

set -euo pipefail

API_KEY="${UPTIMEROBOT_API_KEY:-}"
BASE="https://api.uptimerobot.com/v2"

if [[ -z "$API_KEY" ]]; then
    echo "❌  UPTIMEROBOT_API_KEY not set."
    echo ""
    echo "Setup steps:"
    echo "  1. Sign up free at https://uptimerobot.com"
    echo "  2. Go to My Settings → API Settings"
    echo "  3. Click 'Create Main API Key'"
    echo "  4. Run:  export UPTIMEROBOT_API_KEY='ur_your_key_here'"
    echo "  5. Re-run this script"
    exit 1
fi

echo "🤖  UptimeRobot Monitor Setup for AI Identity"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Step 1: Get alert contacts ──────────────────────────────────────

echo "📬  Fetching alert contacts..."
CONTACTS_RESPONSE=$(curl -s -X POST "$BASE/getAlertContacts" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "api_key=$API_KEY&format=json")

ALERT_CONTACT_ID=$(echo "$CONTACTS_RESPONSE" | jq -r '.alert_contacts[0].id // empty')

if [[ -z "$ALERT_CONTACT_ID" ]]; then
    echo "⚠️  No alert contacts found. Monitors will be created without alerts."
    echo "   Add an alert contact in UptimeRobot dashboard, then re-run."
    ALERT_PARAM=""
else
    echo "   Found alert contact: $ALERT_CONTACT_ID"
    # Format: id_threshold_recurrence (0_0 = default threshold, notify every time)
    ALERT_PARAM="${ALERT_CONTACT_ID}_0_0"
fi

# ── Step 2: Define monitors ─────────────────────────────────────────

# Monitor type 1 = HTTP(s)
# Interval = 300 seconds (5 min, free tier minimum)
declare -A MONITORS
MONITORS=(
    ["AI Identity API"]="https://api.ai-identity.co/health"
    ["AI Identity Gateway"]="https://gateway.ai-identity.co/health"
    ["AI Identity Dashboard"]="https://dashboard.ai-identity.co"
    ["AI Identity Landing"]="https://ai-identity.co"
    ["CEO Dashboard"]="https://ceo.corethread.tech"
)

# ── Step 3: Check existing monitors ─────────────────────────────────

echo ""
echo "🔍  Checking existing monitors..."
EXISTING=$(curl -s -X POST "$BASE/getMonitors" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "api_key=$API_KEY&format=json")

EXISTING_URLS=$(echo "$EXISTING" | jq -r '.monitors[].url // empty' 2>/dev/null || echo "")

# ── Step 4: Create monitors ─────────────────────────────────────────

echo ""
echo "🚀  Creating monitors..."
echo ""

CREATED=0
SKIPPED=0
MONITOR_IDS=()

for NAME in "${!MONITORS[@]}"; do
    URL="${MONITORS[$NAME]}"

    # Skip if already exists
    if echo "$EXISTING_URLS" | grep -qF "$URL"; then
        echo "   ⏭  $NAME — already exists, skipping"
        # Grab existing monitor ID for status page
        MID=$(echo "$EXISTING" | jq -r --arg url "$URL" '.monitors[] | select(.url == $url) | .id')
        MONITOR_IDS+=("$MID")
        ((SKIPPED++))
        continue
    fi

    # Create monitor
    CREATE_DATA="api_key=$API_KEY&format=json&type=1&friendly_name=$NAME&url=$URL&interval=300"
    if [[ -n "$ALERT_PARAM" ]]; then
        CREATE_DATA="$CREATE_DATA&alert_contacts=$ALERT_PARAM"
    fi

    RESULT=$(curl -s -X POST "$BASE/newMonitor" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "$CREATE_DATA")

    STATUS=$(echo "$RESULT" | jq -r '.stat')
    if [[ "$STATUS" == "ok" ]]; then
        MID=$(echo "$RESULT" | jq -r '.monitor.id')
        MONITOR_IDS+=("$MID")
        echo "   ✅  $NAME — created (ID: $MID)"
        ((CREATED++))
    else
        ERROR=$(echo "$RESULT" | jq -r '.error.message // .error // "unknown error"')
        echo "   ❌  $NAME — failed: $ERROR"
    fi
done

echo ""
echo "   Created: $CREATED | Skipped (existing): $SKIPPED"

# ── Step 5: Create public status page ───────────────────────────────

echo ""
echo "📊  Setting up public status page..."

# Check for existing status pages
PAGES_RESPONSE=$(curl -s -X POST "$BASE/getPSPs" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "api_key=$API_KEY&format=json")

EXISTING_PAGE=$(echo "$PAGES_RESPONSE" | jq -r '.psps[] | select(.friendly_name == "AI Identity Status") | .id // empty' 2>/dev/null || echo "")

if [[ -n "$EXISTING_PAGE" ]]; then
    echo "   ⏭  Status page already exists"
    STATUS_PAGE_URL=$(echo "$PAGES_RESPONSE" | jq -r '.psps[] | select(.friendly_name == "AI Identity Status") | .custom_url // .standard_url')
else
    # Build monitor list for status page (format: monitor_id-monitor_id-...)
    MONITOR_LIST=$(IFS=-; echo "${MONITOR_IDS[*]}")

    if [[ -n "$MONITOR_LIST" ]]; then
        PAGE_RESULT=$(curl -s -X POST "$BASE/newPSP" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -d "api_key=$API_KEY&format=json&type=1&friendly_name=AI Identity Status&monitors=$MONITOR_LIST")

        PAGE_STATUS=$(echo "$PAGE_RESULT" | jq -r '.stat')
        if [[ "$PAGE_STATUS" == "ok" ]]; then
            PSP_ID=$(echo "$PAGE_RESULT" | jq -r '.psp.id')
            echo "   ✅  Status page created (ID: $PSP_ID)"
            echo "   🔗  URL: https://stats.uptimerobot.com/your-page-id"
            echo "   💡  Find the exact URL in your UptimeRobot dashboard under Status Pages"
        else
            ERROR=$(echo "$PAGE_RESULT" | jq -r '.error.message // .error // "unknown error"')
            echo "   ⚠️  Status page creation failed: $ERROR"
            echo "   💡  Create manually at https://uptimerobot.com → Status Pages"
        fi
    else
        echo "   ⚠️  No monitor IDs available for status page"
    fi
fi

# ── Summary ──────────────────────────────────────────────────────────

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅  UptimeRobot setup complete!"
echo ""
echo "Monitors (5-min checks):"
for NAME in "${!MONITORS[@]}"; do
    echo "   • $NAME → ${MONITORS[$NAME]}"
done
echo ""
echo "Next steps:"
echo "  1. Verify monitors at https://dashboard.uptimerobot.com"
echo "  2. Add your phone number as an alert contact (for SMS on P0)"
echo "  3. Copy the public status page URL"
echo "  4. Share status page URL with design partners"
echo "  5. Add UPTIMEROBOT_API_KEY to CEO Dashboard .env for Ops page integration"
echo ""
echo "Free tier includes:"
echo "  • 50 monitors"
echo "  • 5-minute check intervals"
echo "  • Email alerts"
echo "  • 1 public status page"
echo "  • 2 months of logs"
