#!/usr/bin/env bash
# Sync a CoSAI WS4 shared Google Doc (exported as .docx) into its git markdown
# snapshot. One-directional: Google Doc -> git. See README.md.
#
# Usage: scripts/cosai-docs/sync.sh <exported.docx> <target.md>
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <exported.docx> <target.md>" >&2
  exit 2
fi

src="$1"
dst="$2"

if [ ! -f "$src" ]; then
  echo "error: source not found: $src" >&2
  exit 1
fi
command -v pandoc >/dev/null || { echo "error: pandoc not installed" >&2; exit 1; }

pandoc -f docx -t gfm "$src" -o "$dst"

echo "Wrote snapshot: $dst"
echo "  (from: $src)"
echo
echo "Next:"
echo "  git --no-pager diff -- '$dst'   # review the change"
echo "  git add '$dst' && git commit     # snapshot it"
echo
echo "Reminder: edit the Google Doc, never a downloaded copy. Internal reviewer"
echo "notes live in a sibling *.notes.md that this sync never touches."
