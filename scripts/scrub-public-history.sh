#!/usr/bin/env bash
# Purge confidential GTM material from the ENTIRE git history of this PUBLIC repo.
#
#   ⚠️  DESTRUCTIVE AND IRREVERSIBLE. Rewrites every commit SHA. Requires a
#       force-push to main and re-clones by every collaborator.
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
# Requires git-filter-repo:  pip install git-filter-repo
#
# See docs/security/public-repo-exposure-remediation.md for the full runbook,
# including the post-push steps this script cannot perform for you.

set -euo pipefail

EXPORT_DIR="${EXPORT_DIR:-../ai-identity-private-export}"

# Paths purged from all of history. Keep in sync with .gitignore and
# scripts/check-no-confidential.sh.
PATHS=(
  marketing/sales
  outreach
  competitive-brief-april-2026.md
  AI_Identity_Budget_Tracker.xlsx
  AI-Identity-Status-Report-2026-04-06.docx
)

command -v git-filter-repo >/dev/null 2>&1 || {
  echo "ERROR: git-filter-repo not found. Install it with:  pip install git-filter-repo"
  exit 1
}

[ -d .git ] || { echo "ERROR: not a git repository."; exit 1; }

if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: working tree is dirty. Commit or stash first."
  exit 1
fi

cat <<EOF

  This will rewrite ALL history in $(pwd)
  Every commit SHA changes. main must then be force-pushed.

  Purging:
$(printf '    - %s\n' "${PATHS[@]}")

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

# ── 2. Rewrite ──────────────────────────────────────────────────────────────
echo "==> Rewriting history"
args=()
for p in "${PATHS[@]}"; do args+=(--path "$p"); done
git filter-repo --invert-paths "${args[@]}" --force

# ── 3. Verify ───────────────────────────────────────────────────────────────
echo "==> Verifying the blobs are gone from all history"
remaining=0
for p in "${PATHS[@]}"; do
  if git log --all --oneline -- "$p" | grep -q .; then
    echo "    STILL PRESENT: $p"
    remaining=1
  fi
done
[ "$remaining" -eq 0 ] && echo "    clean — no history references remain"

cat <<'EOF'

==> Rewrite complete. Remaining steps are MANUAL and must not be skipped:

  1. Re-add the remote (filter-repo drops it deliberately):
       git remote add origin https://github.com/Levaj2000/AI-Identity.git

  2. Force-push every branch and tag:
       git push --force --all origin
       git push --force --tags origin

  3. Tell every collaborator to re-clone. Old clones will otherwise
     reintroduce the purged blobs on their next push.

  4. The old commits stay reachable on GitHub until they are garbage
     collected — via direct SHA URLs, cached views, forks, and any pull
     request that referenced them. Open a GitHub Support request to purge
     the cached views, and check for forks first:
       https://github.com/Levaj2000/AI-Identity/network/members

  5. Treat the exposed material as already public. Anything in the pipeline
     CSV or outreach list should be assumed read: rotate nothing (no
     credentials leaked), but do not rely on the rewrite for secrecy.

EOF
