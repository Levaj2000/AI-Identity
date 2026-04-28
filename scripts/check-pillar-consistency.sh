#!/usr/bin/env bash
# Enforce the Four Pillars canon (Identity, Policy, Compliance, Forensics).
# See .claude/brand-voice-guidelines.md.
#
# Fails if any tracked file under landing-page/, docs/, or marketing/ contains
# the phrase "three pillar" (case-insensitive), with the exception of the
# brand voice guide itself, the changelog, and this script.

set -euo pipefail

PATTERN='\b[Tt]hree[ -]?[Pp]illar'
SEARCH_DIRS=(landing-page docs marketing)

ALLOWED_PATHS=(
  ".claude/brand-voice-guidelines.md"
  "CHANGELOG.md"
  "scripts/check-pillar-consistency.sh"
  "landing-page/src/app/changelog/page.tsx"
)

is_allowed() {
  local file="$1"
  for allowed in "${ALLOWED_PATHS[@]}"; do
    if [[ "$file" == *"$allowed" ]]; then
      return 0
    fi
  done
  return 1
}

violations=""
for dir in "${SEARCH_DIRS[@]}"; do
  [ -d "$dir" ] || continue
  while IFS= read -r line; do
    file="${line%%:*}"
    if ! is_allowed "$file"; then
      violations+="$line"$'\n'
    fi
  done < <(grep -rn -i -E "$PATTERN" \
    --include='*.ts' --include='*.tsx' \
    --include='*.js' --include='*.jsx' \
    --include='*.html' --include='*.md' --include='*.mdx' \
    --exclude-dir=dist --exclude-dir=.next --exclude-dir=node_modules \
    "$dir" 2>/dev/null || true)
done

if [ -n "$violations" ]; then
  echo "✗ Brand voice violation: Four Pillars is canonical."
  echo "  Identity → Policy → Compliance → Forensics (always in this order)."
  echo "  See .claude/brand-voice-guidelines.md."
  echo
  printf '%s' "$violations"
  exit 1
fi

exit 0
