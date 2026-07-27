#!/usr/bin/env bash
# Purge confidential GTM material — and the personal email addresses — from the
# history of this PUBLIC repo.
#
#   ⚠️  DESTRUCTIVE AND IRREVERSIBLE. Rewrites every commit SHA on main.
#       Requires a force-push and re-clones by every collaborator.
#
# Deleting a file in a normal commit does NOT unpublish it — the blob stays
# reachable in history and through the GitHub UI forever. Only a history
# rewrite removes it.
#
# Run this from a FRESH clone, not your working copy:
#
#     git clone https://github.com/Levaj2000/AI-Identity.git ai-identity-scrub
#     cd ai-identity-scrub
#     ./scripts/scrub-public-history.sh
#
# Requires git-filter-repo:  brew install git-filter-repo
#
# See docs/security/public-repo-exposure-remediation.md for the full runbook,
# including the post-push steps this script cannot perform for you.

set -euo pipefail

EXPORT_DIR="${EXPORT_DIR:-../ai-identity-private-export}"

# Paths purged from history. Keep in sync with .gitignore and
# scripts/check-no-confidential.sh.
PATHS=(
  marketing/sales
  outreach
  competitive-brief-april-2026.md
  AI_Identity_Budget_Tracker.xlsx
  AI-Identity-Status-Report-2026-04-06.docx
)

# Only main is rewritten. See the evidence-anchor-mirror guard below for why
# that is deliberate rather than lazy.
TARGET_REF="refs/heads/main"

# This tag exists solely to keep commit 92458691 reachable for SHA-pinned links
# in ocsf/ocsf-schema#1689. That commit also carries 35 confidential files, so
# leaving the tag in place would defeat this entire script.
LINK_TAG="ocsf-1689-sample-artifacts"

command -v git-filter-repo >/dev/null 2>&1 || {
  echo "ERROR: git-filter-repo not found. Install it with:  brew install git-filter-repo"
  exit 1
}

[ -d .git ] || { echo "ERROR: not a git repository."; exit 1; }

if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: working tree is dirty. Commit or stash first."
  exit 1
fi

# ── Guard: the link tag keeps the confidential blobs alive ───────────────────
if git rev-parse -q --verify "refs/tags/$LINK_TAG" >/dev/null; then
  cat <<EOF
ERROR: tag '$LINK_TAG' still exists.

  It pins commit 92458691, whose tree carries 35 confidential files. Purging
  main while that tag survives leaves the material reachable and makes this
  script a no-op in practice.

  All nine files the OCSF #1689 comment links to are ALSO on main, so no
  content is lost by dropping the tag — only the SHA-pinned URLs break, on a
  PR that has been closed since 2026-07-16.

  Decide first, then re-run:
    (a) Accept the dead links   — git tag -d $LINK_TAG
                                  git push origin :refs/tags/$LINK_TAG
    (b) Preserve the record     — edit the #1689 comment to point at
                                  blob/main/docs/... paths, THEN do (a).
EOF
  exit 1
fi

# ── Identity inputs, validated BEFORE anything is exported or destroyed ──────
# The addresses are NEVER stored in this file. An earlier revision hardcoded
# them and published both to this public repo — the exact class of leak this
# script exists to remove. Supply them at run time:
#
#   SCRUB_FOUNDER_EMAIL=... SCRUB_OTHER_EMAIL=... ./scripts/scrub-public-history.sh
#
# Each value is checked against the SHA-256 backstop already published in
# common/queries/user_cleanup.py, so a typo fails here — cheaply, before the
# export and the rewrite — rather than silently rewriting nothing and
# reporting success.
NOREPLY="${SCRUB_NOREPLY_EMAIL:-120221487+Levaj2000@users.noreply.github.com}"
FOUNDER="${SCRUB_FOUNDER_EMAIL:-}"
OTHER="${SCRUB_OTHER_EMAIL:-}"

# Same values as _PROTECTED_EMAIL_HASHES in common/queries/user_cleanup.py.
EXPECTED_HASHES="
6ad13664ba4f2fdbbfedbaea18f4c8167425cd3881ec341c57b65c53aaec4f69
16ed82df9608ecc8096756eca2fd5e90c0ab10013be157b14afc34ad3361dfb7
"

check_addr() {  # $1 = address, $2 = variable name for the error message
  local h
  h=$(printf '%s' "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" | sha256sum | cut -d' ' -f1)
  if ! grep -qx "$h" <<<"$(tr -d ' ' <<<"$EXPECTED_HASHES")"; then
    echo "ERROR: \$$2 does not match either known address (compared by SHA-256,"
    echo "       so this script never has to contain them). Fix it and re-run."
    exit 1
  fi
}

IDENTITY_REWRITE=0
if [ -n "$FOUNDER" ] || [ -n "$OTHER" ]; then
  [ -n "$FOUNDER" ] && check_addr "$FOUNDER" SCRUB_FOUNDER_EMAIL
  [ -n "$OTHER" ]   && check_addr "$OTHER"   SCRUB_OTHER_EMAIL
  IDENTITY_REWRITE=1
fi

# ── Guard: never rewrite the evidence mirror ─────────────────────────────────
# evidence-anchor-mirror is an orphan branch holding the public, append-only
# Evidence Anchor checkpoint record. Its whole value is that it has never been
# rewritten — "the existing branch is the evidence." It carries no confidential
# paths, so there is nothing to purge there, and rewriting it would damage the
# one property it exists to provide.
if git rev-parse -q --verify refs/heads/evidence-anchor-mirror >/dev/null; then
  echo "==> evidence-anchor-mirror present — it will NOT be rewritten or pushed."
fi

cat <<EOF

  This rewrites $TARGET_REF in $(pwd)
  Every commit SHA on main changes. main must then be force-pushed.

  Purging paths:
$(printf '    - %s\n' "${PATHS[@]}")

  Also rewriting:
    - author/committer email  ->  the GitHub noreply address
    - both personal addresses out of blob content and commit messages

  NOT touched: evidence-anchor-mirror (append-only evidence record)

EOF
read -r -p "  Type 'rewrite' to continue: " confirm
[ "$confirm" = "rewrite" ] || { echo "Aborted."; exit 1; }

# ── 1. Preserve the content before it is destroyed ──────────────────────────
# These files are still wanted — just not publicly. Copy them out first.
echo "==> Exporting confidential material to $EXPORT_DIR"
mkdir -p "$EXPORT_DIR"
for p in "${PATHS[@]}"; do
  if [ -e "$p" ]; then
    mkdir -p "$EXPORT_DIR/$(dirname "$p")"
    cp -R "$p" "$EXPORT_DIR/$(dirname "$p")/"
    echo "    saved  $p"
  else
    # Already removed from HEAD — recover the last version that existed.
    last=$(git log --format='%H' -n 1 -- "$p" || true)
    if [ -n "$last" ]; then
      mkdir -p "$EXPORT_DIR/$(dirname "$p")"
      git archive "$last^" -- "$p" 2>/dev/null | tar -x -C "$EXPORT_DIR" \
        && echo "    saved  $p (from history @ ${last:0:8})" \
        || echo "    WARN   could not recover $p"
    fi
  fi
done

echo "==> Verifying export is non-empty"
if [ -z "$(ls -A "$EXPORT_DIR" 2>/dev/null)" ]; then
  echo "ERROR: export directory is empty — refusing to destroy the only copy."
  exit 1
fi

# ── 2. Build the identity + text rewrite rules ──────────────────────────────
# Values were read and validated at the top, before anything was destroyed.
# They live only in this temp dir, never in a file inside the repo.
RULES=$(mktemp -d)
trap 'rm -rf "$RULES"' EXIT

if [ "$IDENTITY_REWRITE" -eq 1 ]; then
  : > "$RULES/replace-text"
  if [ -n "$FOUNDER" ]; then
    printf 'Jeff Leva <%s> <%s>\n' "$NOREPLY" "$FOUNDER" > "$RULES/mailmap"
    printf '%s==>%s\n' "$FOUNDER" "$NOREPLY" >> "$RULES/replace-text"
  fi
  [ -n "$OTHER" ] && printf '%s==>[redacted]\n' "$OTHER" >> "$RULES/replace-text"
  cp "$RULES/replace-text" "$RULES/replace-message"
else
  cat <<'EOF'

  NOTE: SCRUB_FOUNDER_EMAIL / SCRUB_OTHER_EMAIL are unset, so this run purges
        PATHS ONLY. Author and committer emails will be left as they are.
        That is a valid mode — just not the full scrub.

EOF
fi

# ── 3. Rewrite ──────────────────────────────────────────────────────────────
echo "==> Rewriting $TARGET_REF"
args=()
for p in "${PATHS[@]}"; do args+=(--path "$p"); done
if [ "$IDENTITY_REWRITE" -eq 1 ]; then
  [ -f "$RULES/mailmap" ] && args+=(--mailmap "$RULES/mailmap")
  args+=(--replace-text "$RULES/replace-text" --replace-message "$RULES/replace-message")
fi
git filter-repo --refs "$TARGET_REF" --invert-paths "${args[@]}" --force

# ── 4. Verify — a failure here is FATAL ─────────────────────────────────────
echo "==> Verifying"
remaining=0
for p in "${PATHS[@]}"; do
  if git log "$TARGET_REF" --oneline -- "$p" | grep -q .; then
    echo "    STILL PRESENT: $p"
    remaining=1
  fi
done

if [ "$IDENTITY_REWRITE" -eq 1 ] && [ -n "$FOUNDER" ]; then
  if git log "$TARGET_REF" --format='%ae%n%ce' | grep -qF "$FOUNDER"; then
    echo "    STILL PRESENT: personal address in author/committer fields"
    remaining=1
  fi
fi

if [ "$remaining" -ne 0 ]; then
  echo
  echo "ERROR: the rewrite did not fully clean $TARGET_REF. Do NOT force-push."
  echo "       Investigate first — pushing now would burn the force-push"
  echo "       without achieving the purge."
  exit 1
fi
echo "    clean — no confidential paths and no personal addresses remain on main"

cat <<EOF

==> Rewrite complete. Remaining steps are MANUAL and must not be skipped:

  1. Re-add the remote (filter-repo drops it deliberately):
       git remote add origin https://github.com/Levaj2000/AI-Identity.git

  2. Force-push MAIN ONLY. Do NOT use --all: that would push a rewritten
     evidence-anchor-mirror, damaging the append-only evidence record.
       git push --force origin main

  3. Delete the stale tag on the remote if you have not already:
       git push origin :refs/tags/$LINK_TAG

  4. Tell every collaborator to re-clone. Old clones will otherwise
     reintroduce the purged blobs on their next push.

  5. The old commits stay reachable on GitHub until they are garbage
     collected — via direct SHA URLs, cached views, forks, and any pull
     request that referenced them. Open a GitHub Support request to purge
     the cached views, and check for forks first:
       https://github.com/Levaj2000/AI-Identity/network/members

  6. Treat the exposed material as already public. Anything in the pipeline
     CSV or outreach list should be assumed read: rotate nothing (no
     credentials leaked), but do not rely on the rewrite for secrecy.

EOF
