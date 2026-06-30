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
dst_name="$(basename "$dst")"

if [ ! -f "$src" ]; then
  echo "error: source not found: $src" >&2
  exit 1
fi

case "$dst_name" in
  *.notes.md)
    echo "error: refusing to sync into internal notes target: $dst" >&2
    echo "       choose the collaborator-safe snapshot .md listed in scripts/cosai-docs/README.md" >&2
    exit 1
    ;;
  *.md)
    ;;
  *)
    echo "error: target must be a markdown snapshot (*.md): $dst" >&2
    exit 1
    ;;
esac

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
