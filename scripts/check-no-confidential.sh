#!/usr/bin/env bash
# Block confidential material from entering the PUBLIC repo.
#
# .gitignore is the first line of defence, but it is trivially bypassed with
# `git add -f` and does nothing for paths nobody thought to list. This hook is
# the second line: it inspects what is actually STAGED and fails the commit.
#
# Two modes, one set of patterns:
#   (no args)              inspect the index — the pre-commit hook.
#   --range <base> <head>  inspect a commit range — CI, where nothing is
#                          staged. Hooks are per-clone and skippable with
#                          --no-verify; CI is the backstop that is neither.
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
# Directory prefixes anchor at the repo root; filename patterns match at ANY
# depth — `.gitignore` matches them at any depth too, and this hook exists to
# backstop the `git add -f` that bypasses `.gitignore`. A root-only filename
# pattern would leave docs/competitive-brief-*.md unguarded.
FORBIDDEN_PATHS='^(private/|marketing/sales/|outreach/)|(^|/)competitive-brief-[^/]*\.md$|(^|/)[^/]*Budget_Tracker[^/]*\.xlsx$|(^|/)AI-Identity-Status-Report-[^/]*\.docx$'

# ── Content: SHA-256 of lowercased addresses that must never be committed ───
FORBIDDEN_EMAIL_HASHES="
6ad13664ba4f2fdbbfedbaea18f4c8167425cd3881ec341c57b65c53aaec4f69
16ed82df9608ecc8096756eca2fd5e90c0ab10013be157b14afc34ad3361dfb7
"

# No file is exempt from the email scan. The hashes themselves are not
# email-shaped, so files that legitimately carry them (this script,
# common/queries/user_cleanup.py) pass without an allowlist — and an allowlist
# would mean a plaintext address re-added to exactly those files went unnoticed.

# ── Mode ────────────────────────────────────────────────────────────────────
MODE=staged
BASE=""
HEAD_REV=""
if [ "${1:-}" = "--range" ]; then
  MODE=range
  BASE="${2:?--range needs a base revision}"
  HEAD_REV="${3:?--range needs a head revision}"
fi

# The set of files to inspect.
staged() {
  if [ "$MODE" = range ]; then
    # Three-dot: everything the branch adds since it diverged, so a violation
    # introduced in an early commit and left in place is still caught.
    git diff --name-only --diff-filter=ACMR "$BASE...$HEAD_REV"
  else
    git diff --cached --name-only --diff-filter=ACMR
  fi
}

# The content that would land on main, for a path from staged().
read_blob() {
  if [ "$MODE" = range ]; then
    git show "$HEAD_REV:$1"
  else
    git show ":$1"
  fi
}

blob=$(mktemp)
trap 'rm -f "$blob"' EXIT

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
  # Read the STAGED blob, never the worktree copy. Partial staging (`git add
  # -p`, or an edit made after `git add`) means the two differ, and it is the
  # staged version that gets committed — scanning the worktree lets an address
  # staged and then edited out of the file sail straight through. In range
  # mode the equivalent is the blob at HEAD, not the runner's checkout.
  read_blob "$file" >"$blob" 2>/dev/null || continue
  # Skip binaries.
  grep -Iq . "$blob" 2>/dev/null || continue

  while IFS= read -r addr; do
    [ -n "$addr" ] || continue
    hash=$(printf '%s' "$(printf '%s' "$addr" | tr '[:upper:]' '[:lower:]')" \
      | sha256sum | cut -d' ' -f1)
    if grep -qx "$hash" <<<"$(tr -d ' ' <<<"$FORBIDDEN_EMAIL_HASHES")"; then
      violations+="  [email] $file — contains a personal address that must not be published"$'\n'
      break
    fi
  done < <(grep -oIE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' "$blob" 2>/dev/null | sort -u)
done < <(staged)

if [ -n "$violations" ]; then
  if [ "$MODE" = range ]; then
    echo "✗ Confidential material in these changes — this is a PUBLIC repository."
  else
    echo "✗ Confidential material staged for a PUBLIC repository."
  fi
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
