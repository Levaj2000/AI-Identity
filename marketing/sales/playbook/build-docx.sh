#!/usr/bin/env bash
# Convert a filled-in markdown deliverable to a Word .docx for sending.
#
# Usage:   ./build-docx.sh <input.md> [output.docx]
# Example: ./build-docx.sh ../engagements/standard-motor/01-discovery-summary.md
#          ./build-docx.sh ../engagements/standard-motor/02-scoping-doc.md
#
# Requires pandoc (already installed: /opt/homebrew/bin/pandoc).
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <input.md> [output.docx]" >&2
  exit 1
fi

IN="$1"
OUT="${2:-${IN%.md}.docx}"

if [[ ! -f "$IN" ]]; then
  echo "Input file not found: $IN" >&2
  exit 1
fi

pandoc "$IN" -o "$OUT" --reference-doc="$(dirname "$0")/templates/discovery-summary-template.docx" 2>/dev/null \
  || pandoc "$IN" -o "$OUT"

echo "Saved: $OUT"
