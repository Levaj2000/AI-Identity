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
#       MacOS/launcher          (shim that execs the LIVE source script)
#       Resources/
#         ada.icns
#
# The launcher script (agent/Launch Ada.command) is deliberately NOT bundled.
# The shim execs it from its source path so edits go live without rebuilding
# the .app. Rebuild only when icon, Info.plist, or shim itself changes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIST="${AGENT_DIR}/dist"
APP="${DIST}/Launch Ada.app"
ICON="${SCRIPT_DIR}/ada.icns"

# CMD is what we bake into the shim — it must point at the canonical main
# checkout, not whatever worktree happens to be invoking this script. Resolve
# via git's common dir, which is shared across all worktrees of the same repo.
# Override with MAIN_CHECKOUT=/path/to/AI-Identity if you've stashed the repo
# somewhere unusual.
if [[ -n "${MAIN_CHECKOUT:-}" ]]; then
  MAIN_AGENT="${MAIN_CHECKOUT}/agent"
else
  COMMON_GIT_DIR="$(git -C "${AGENT_DIR}" rev-parse --git-common-dir 2>/dev/null || true)"
  if [[ -z "${COMMON_GIT_DIR}" ]]; then
    echo "ERROR: not inside a git repo (or git unavailable). Set MAIN_CHECKOUT=/path/to/AI-Identity and rerun." >&2
    exit 1
  fi
  # --git-common-dir can be relative; normalize via cd+pwd.
  COMMON_GIT_DIR="$(cd "$(dirname "${COMMON_GIT_DIR}")/$(basename "${COMMON_GIT_DIR}")" && pwd)"
  MAIN_AGENT="$(cd "${COMMON_GIT_DIR}/.." && pwd)/agent"
fi
CMD="${MAIN_AGENT}/Launch Ada.command"

if [[ ! -f "${CMD}" ]]; then
  echo "ERROR: missing ${CMD}" >&2
  echo "       (Resolved from $(if [[ -n "${MAIN_CHECKOUT:-}" ]]; then echo "MAIN_CHECKOUT env"; else echo "git --git-common-dir"; fi).)" >&2
  exit 1
fi
echo "▸ shim will exec: ${CMD}"

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

# We deliberately do NOT copy the .command script into the bundle. The shim
# below execs the live source path baked in at build time — so editing
# agent/Launch Ada.command is reflected on the next double-click without
# rebuilding the .app. The .app is a stable shell; the script is the brain.

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

cat > "${APP}/Contents/MacOS/launcher" <<SH
#!/usr/bin/env bash
# Tiny shim: open the LIVE source script (path baked in at build time) in
# Terminal so the user gets a window with logs and Ctrl-C support, then exit
# the .app process immediately.
#
# The script path is intentionally outside the bundle — that way editing the
# launcher logic in the repo is reflected on the next double-click without a
# rebuild. The .app only needs to be rebuilt for icon, Info.plist, or shim
# changes. If the source script is missing (repo deleted or moved), Terminal
# will show an error rather than silently running stale code.
SRC="${CMD}"
if [[ ! -f "\${SRC}" ]]; then
  osascript -e "display dialog \"Ada launcher source script is missing:\\n\${SRC}\\n\\nThe AI-Identity repo may have moved. Re-run build_launcher.sh.\" buttons {\"OK\"} with icon stop"
  exit 1
fi
open -a Terminal "\${SRC}"
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
