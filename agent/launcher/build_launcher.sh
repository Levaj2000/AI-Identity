#!/usr/bin/env bash
# build_launcher.sh — assemble `Launch Ada.app` from sources.
#
#   bash agent/launcher/build_launcher.sh                 # build only
#   bash agent/launcher/build_launcher.sh --install       # also copy to ~/Desktop
#
# What's built:
#   agent/dist/Launch Ada.app/
#     Contents/
#       Info.plist
#       MacOS/launcher          (small shell shim)
#       Resources/
#         ada.icns
#         Launch Ada.command    (the actual server-launcher script)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIST="${AGENT_DIR}/dist"
APP="${DIST}/Launch Ada.app"
ICON="${SCRIPT_DIR}/ada.icns"
CMD="${AGENT_DIR}/Launch Ada.command"

if [[ ! -f "${CMD}" ]]; then
  echo "ERROR: missing ${CMD}" >&2
  exit 1
fi

# (Re)build the icon if it's stale or missing.
if [[ ! -f "${ICON}" || "${SCRIPT_DIR}/build_icon.py" -nt "${ICON}" ]]; then
  # Find a usable Python: prefer local .venv, fall back to main checkout, then PATH.
  PY=""
  for cand in \
    "${AGENT_DIR}/.venv/bin/python" \
    "/Users/jeffleva/Dev/AI-Identity/agent/.venv/bin/python" \
    "$(command -v python3 || true)"; do
    if [[ -x "${cand}" ]]; then PY="${cand}"; break; fi
  done
  if [[ -z "${PY}" ]]; then
    echo "ERROR: no Python found. Set up the venv: cd ${AGENT_DIR} && python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 1
  fi
  echo "▸ generating icon with ${PY}…"
  "${PY}" -c "import PIL" 2>/dev/null || "${PY}" -m pip install --quiet --user Pillow || "${PY}" -m pip install --quiet Pillow
  "${PY}" "${SCRIPT_DIR}/build_icon.py"
fi

echo "▸ assembling ${APP}"
rm -rf "${APP}"
mkdir -p "${APP}/Contents/MacOS" "${APP}/Contents/Resources"

cp "${ICON}" "${APP}/Contents/Resources/ada.icns"
cp "${CMD}"  "${APP}/Contents/Resources/Launch Ada.command"
chmod +x     "${APP}/Contents/Resources/Launch Ada.command"

cat > "${APP}/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Launch Ada</string>
  <key>CFBundleDisplayName</key><string>Launch Ada</string>
  <key>CFBundleIdentifier</key><string>co.ai-identity.ada.launcher</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>launcher</string>
  <key>CFBundleIconFile</key><string>ada</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <!-- LSUIElement keeps it out of the Dock; we use Terminal for the visible UI. -->
  <key>LSUIElement</key><false/>
</dict>
</plist>
PLIST

cat > "${APP}/Contents/MacOS/launcher" <<'SH'
#!/usr/bin/env bash
# Tiny shim: open the bundled .command in Terminal so the user gets a window
# with logs and Ctrl-C support, then exit the .app process immediately.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
open -a Terminal "${DIR}/Resources/Launch Ada.command"
SH
chmod +x "${APP}/Contents/MacOS/launcher"

# Touch the bundle so Finder/LaunchServices re-reads the icon.
touch "${APP}"

echo "✓ built ${APP}"

if [[ "${1:-}" == "--install" ]]; then
  DEST="${HOME}/Desktop/Launch Ada.app"
  rm -rf "${DEST}"
  cp -R "${APP}" "${DEST}"
  touch "${DEST}"
  echo "✓ copied to ${DEST}"
fi
