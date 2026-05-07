#!/usr/bin/env bash
# build_launcher.sh — assemble `Launch Ada.app` from sources.
#
# DEFAULT (menu-bar mode):
#   bash agent/launcher/build_launcher.sh               # build menu-bar .app
#   bash agent/launcher/build_launcher.sh --install     # also copy to ~/Desktop
#
# TERMINAL FALLBACK (original behaviour — Terminal window pops up):
#   bash agent/launcher/build_launcher.sh --terminal-mode
#   bash agent/launcher/build_launcher.sh --terminal-mode --install
#
# WHY menu-bar is the default:
#   The new rumps-based app removes the Terminal window entirely.  The old
#   shim (--terminal-mode) is kept for debugging and for users who want live
#   log streaming in a visible Terminal window.
#
# What the menu-bar build produces:
#   agent/dist/Launch Ada.app/
#     Contents/
#       Info.plist               (LSUIElement=true → no Dock badge)
#       MacOS/launcher           (exec venv python menubar_app.py)
#       Resources/
#         ada.icns
#         ada_menubar.png        (22-pt PNG for the status-bar icon)
#         menubar_app.py         (bundled so edits in-repo take effect after rebuild)
#
# What the terminal build produces (same as PR #214):
#   agent/dist/Launch Ada.app/
#     Contents/
#       Info.plist               (LSUIElement=false)
#       MacOS/launcher           (open -a Terminal "agent/Launch Ada.command")
#       Resources/ada.icns

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIST="${AGENT_DIR}/dist"
APP="${DIST}/Launch Ada.app"
ICON="${SCRIPT_DIR}/ada.icns"

# ---------------------------------------------------------------------------
# Parse flags
# ---------------------------------------------------------------------------

MENUBAR=true
INSTALL=false

for arg in "$@"; do
  case "${arg}" in
    --terminal-mode) MENUBAR=false ;;
    --install)       INSTALL=true  ;;
    --menubar)       MENUBAR=true  ;;  # explicit, same as default
    *)
      echo "Unknown flag: ${arg}" >&2
      echo "Usage: $0 [--menubar] [--terminal-mode] [--install]" >&2
      exit 1
      ;;
  esac
done

if ${MENUBAR}; then
  echo "▸ mode: menu-bar (rumps)"
else
  echo "▸ mode: terminal (legacy shim)"
fi

# ---------------------------------------------------------------------------
# Resolve the canonical agent path (used only in terminal-mode shim)
# ---------------------------------------------------------------------------

if ${MENUBAR}; then
  # menu-bar mode resolves paths at runtime via _find_agent_dir() in menubar_app.py
  MAIN_AGENT="${AGENT_DIR}"
else
  if [[ -n "${MAIN_CHECKOUT:-}" ]]; then
    MAIN_AGENT="${MAIN_CHECKOUT}/agent"
  else
    COMMON_GIT_DIR="$(git -C "${AGENT_DIR}" rev-parse --git-common-dir 2>/dev/null || true)"
    if [[ -z "${COMMON_GIT_DIR}" ]]; then
      echo "ERROR: not inside a git repo. Set MAIN_CHECKOUT=/path/to/AI-Identity and rerun." >&2
      exit 1
    fi
    COMMON_GIT_DIR="$(cd "$(dirname "${COMMON_GIT_DIR}")/$(basename "${COMMON_GIT_DIR}")" && pwd)"
    MAIN_AGENT="$(cd "${COMMON_GIT_DIR}/.." && pwd)/agent"
  fi
  CMD="${MAIN_AGENT}/Launch Ada.command"
  if [[ ! -f "${CMD}" ]]; then
    echo "ERROR: missing ${CMD}" >&2
    exit 1
  fi
  echo "▸ shim will exec: ${CMD}"
fi

# ---------------------------------------------------------------------------
# Find Python
# ---------------------------------------------------------------------------

PY=""
for cand in \
  "${AGENT_DIR}/.venv/bin/python" \
  "/Users/jeffleva/Dev/AI-Identity/agent/.venv/bin/python" \
  "$(command -v python3 || true)"; do
  if [[ -x "${cand}" ]]; then PY="${cand}"; break; fi
done

if [[ -z "${PY}" ]]; then
  echo "ERROR: no Python found. Set up the venv:" >&2
  echo "  cd ${AGENT_DIR} && python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Build icon (regenerate if stale or missing)
# ---------------------------------------------------------------------------

if [[ ! -f "${ICON}" || "${SCRIPT_DIR}/build_icon.py" -nt "${ICON}" ]]; then
  echo "▸ generating icon with ${PY}…"
  "${PY}" -c "import PIL" 2>/dev/null \
    || "${PY}" -m pip install --quiet --user Pillow \
    || "${PY}" -m pip install --quiet Pillow
  "${PY}" "${SCRIPT_DIR}/build_icon.py"
fi

# ---------------------------------------------------------------------------
# Install launcher requirements (menu-bar mode only)
# ---------------------------------------------------------------------------

if ${MENUBAR}; then
  echo "▸ checking launcher requirements (rumps, Pillow)…"
  LAUNCHER_REQS="${SCRIPT_DIR}/requirements.txt"
  if [[ ! -f "${LAUNCHER_REQS}" ]]; then
    echo "ERROR: ${LAUNCHER_REQS} not found" >&2
    exit 1
  fi
  "${PY}" -c "import rumps" 2>/dev/null \
    || { echo "  ▸ installing rumps…"; "${PY}" -m pip install --quiet -r "${LAUNCHER_REQS}"; }
fi

# ---------------------------------------------------------------------------
# Generate menu-bar PNG icon (menu-bar mode)
# ---------------------------------------------------------------------------

MENUBAR_PNG="${SCRIPT_DIR}/ada_menubar.png"
if ${MENUBAR}; then
  if [[ ! -f "${MENUBAR_PNG}" || "${SCRIPT_DIR}/build_icon.py" -nt "${MENUBAR_PNG}" ]]; then
    echo "▸ generating ada_menubar.png…"
    "${PY}" - <<'PYEOF'
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if False else
                os.path.join(os.environ.get("SCRIPT_DIR", "."), ""))
# Inline: generate a 44×44 @2x PNG for the menu bar.
from PIL import Image, ImageDraw
here = os.environ["SCRIPT_DIR"]
size = 44
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=9, fill=(139, 92, 246, 255))
cx = size // 2
draw.polygon([(cx, 5), (size - 7, size - 7), (7, size - 7)], outline=(255, 255, 255, 220))
draw.line([(12, size - 17), (size - 12, size - 17)], fill=(255, 255, 255, 220), width=2)
out = os.path.join(here, "ada_menubar.png")
img.save(out, "PNG")
print(f"wrote {out}")
PYEOF
  fi
fi

# ---------------------------------------------------------------------------
# Assemble the .app bundle
# ---------------------------------------------------------------------------

echo "▸ assembling ${APP}"
rm -rf "${APP}"
mkdir -p "${APP}/Contents/MacOS" "${APP}/Contents/Resources"

cp "${ICON}" "${APP}/Contents/Resources/ada.icns"

if ${MENUBAR}; then
  # Bundle menubar_app.py and the menu-bar icon into Resources/.
  cp "${SCRIPT_DIR}/menubar_app.py" "${APP}/Contents/Resources/menubar_app.py"
  if [[ -f "${MENUBAR_PNG}" ]]; then
    cp "${MENUBAR_PNG}" "${APP}/Contents/Resources/ada_menubar.png"
  fi
fi

# ---- Info.plist -----------------------------------------------------------

if ${MENUBAR}; then
  LSUI_ELEMENT="true"
  DISPLAY_NAME="Ada"
else
  LSUI_ELEMENT="false"
  DISPLAY_NAME="Launch Ada"
fi

cat > "${APP}/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>${DISPLAY_NAME}</string>
  <key>CFBundleDisplayName</key><string>${DISPLAY_NAME}</string>
  <key>CFBundleIdentifier</key><string>co.ai-identity.ada.launcher</string>
  <key>CFBundleVersion</key><string>2</string>
  <key>CFBundleShortVersionString</key><string>2.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>launcher</string>
  <key>CFBundleIconFile</key><string>ada</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <!-- LSUIElement=true hides the app from the Dock and app switcher.
       Menu-bar-only apps (agents, utilities) should set this to true.
       Set to false in terminal-mode so the Terminal window is the UI. -->
  <key>LSUIElement</key><${LSUI_ELEMENT}/>
</dict>
</plist>
PLIST

# ---- MacOS/launcher shim --------------------------------------------------

if ${MENUBAR}; then
  BAKED_PY="${PY}"
  cat > "${APP}/Contents/MacOS/launcher" <<SH
#!/usr/bin/env bash
# Menu-bar launcher: exec the venv Python with menubar_app.py (bundled in Resources/).
# venv Python path baked at build time; rebuild if you recreate the venv or move the repo.
RESOURCES="\$(cd "\$(dirname "\$0")/../Resources" && pwd)"
MENUBAR_APP="\${RESOURCES}/menubar_app.py"
PY="${BAKED_PY}"

if [[ ! -f "\${MENUBAR_APP}" ]]; then
  osascript -e "display dialog \"Ada: menubar_app.py missing from bundle.\\nRe-run build_launcher.sh --menubar.\" buttons {\"OK\"} with icon stop"
  exit 1
fi
if [[ ! -x "\${PY}" ]]; then
  osascript -e "display dialog \"Ada: Python venv not found at:\\n\${PY}\\n\\nSet up the venv and rebuild.\" buttons {\"OK\"} with icon stop"
  exit 1
fi

exec "\${PY}" "\${MENUBAR_APP}"
SH
else
  # Terminal-mode shim (original PR #214 behaviour).
  CMD_PATH="${CMD}"
  cat > "${APP}/Contents/MacOS/launcher" <<SH
#!/usr/bin/env bash
# Terminal-mode shim: opens the LIVE source script in a Terminal window.
# Path baked in at build time; rebuild if the repo moves.
SRC="${CMD_PATH}"
if [[ ! -f "\${SRC}" ]]; then
  osascript -e "display dialog \"Ada launcher source script is missing:\\n\${SRC}\\n\\nThe AI-Identity repo may have moved. Re-run build_launcher.sh.\" buttons {\"OK\"} with icon stop"
  exit 1
fi
open -a Terminal "\${SRC}"
SH
fi

chmod +x "${APP}/Contents/MacOS/launcher"

# Touch the bundle so Finder / LaunchServices re-reads the icon.
touch "${APP}"

echo "✓ built ${APP}"
if ${MENUBAR}; then
  echo "  (menu-bar mode — no Terminal window, LSUIElement=true)"
else
  echo "  (terminal mode — opens a Terminal window on launch)"
fi

if ${INSTALL}; then
  DEST="${HOME}/Desktop/Launch Ada.app"
  rm -rf "${DEST}"
  cp -R "${APP}" "${DEST}"
  touch "${DEST}"
  echo "✓ copied to ${DEST}"
fi
