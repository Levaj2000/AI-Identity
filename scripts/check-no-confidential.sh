#!/usr/bin/env bash
# Block confidential material from entering the PUBLIC repo.
#
# .gitignore is the first line of defence, but it is trivially bypassed with
# `git add -f` and does nothing for paths nobody thought to list. This hook is
# the second line: it inspects what is actually STAGED and fails the commit.
#
# Two classes of violation:
#   1. Path patterns — GTM material that must live outside the repo
#      (named prospects, deal risk, pricing, spend, internal status).
#   2. Content patterns — personal email addresses that must not be published,
#      matched by SHA-256 so this script does not itself leak them.
#
# See docs/security/public-repo-exposure-remediation.md.

set -euo pipefail

# ── Path patterns (extended regex, matched against staged paths) ────────────
FORBIDDEN_PATHS='^(private/|marketing/sales/|outreach/|competitive-brief-.*\.md$|.*Budget_Tracker.*\.xlsx$|AI-Identity-Status-Report-.*\.docx$)'

# ── Content: SHA-256 of lowercased addresses that must never be committed ───
FORBIDDEN_EMAIL_HASHES="
6ad13664ba4f2fdbbfedbaea18f4c8167425cd3881ec341c57b65c53aaec4f69
16ed82df9608ecc8096756eca2fd5e90c0ab10013be157b14afc34ad3361dfb7
"

# No file is exempt from the email scan. The hashes themselves are not
# email-shaped, so files that legitimately carry them (this script,
# common/queries/user_cleanup.py) pass without an allowlist — and an allowlist
# would mean a plaintext address re-added to exactly those files went unnoticed.

staged() {
  git diff --cached --name-only --diff-filter=ACMR
}

violations=""

# ── 1. Forbidden paths ──────────────────────────────────────────────────────
while IFS= read -r file; do
  [ -n "$file" ] || continue
  if [[ "$file" =~ $FORBIDDEN_PATHS ]]; then
    violations+="  [path]  $file"$'\n'
  fi
done < <(staged)

# ── 2. Forbidden addresses in staged content ────────────────────────────────
# Extract every email-shaped token, hash it, compare. Never prints the address.
while IFS= read -r file; do
  [ -n "$file" ] || continue
  # Skip binaries and anything already gone from the worktree.
  [ -f "$file" ] || continue
  grep -Iq . "$file" 2>/dev/null || continue

  while IFS= read -r addr; do
    [ -n "$addr" ] || continue
    hash=$(printf '%s' "$(printf '%s' "$addr" | tr '[:upper:]' '[:lower:]')" \
      | sha256sum | cut -d' ' -f1)
    if grep -qx "$hash" <<<"$(tr -d ' ' <<<"$FORBIDDEN_EMAIL_HASHES")"; then
      violations+="  [email] $file — contains a personal address that must not be published"$'\n'
      break
    fi
  done < <(grep -oIE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' "$file" 2>/dev/null | sort -u)
done < <(staged)

if [ -n "$violations" ]; then
  echo "✗ Confidential material staged for a PUBLIC repository."
  echo
  printf '%s' "$violations"
  echo
  echo "  Path hits:  keep this material outside the repo (private/ is gitignored)."
  echo "  Email hits: use a role alias, or the hash backstop in"
  echo "              common/queries/user_cleanup.py."
  echo
  echo "  Context: docs/security/public-repo-exposure-remediation.md"
  exit 1
fi

exit 0
