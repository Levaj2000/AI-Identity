#!/usr/bin/env bash
# Launch Ada — double-clickable Mac launcher.
#
# What it does:
#   1. If Ada is already serving on http://127.0.0.1:8000, just open a browser tab.
#   2. Otherwise: cd to the agent dir, activate the venv, start serve.py, wait
#      for /health to come up, then open the browser. Keeps this Terminal window
#      open so you can see logs and Ctrl-C to stop.
#
# Use directly by double-clicking, or via the wrapping `Launch Ada.app` built
# by `build_launcher.sh`.

set -u

PORT=8000
URL="http://127.0.0.1:${PORT}"

# Resolve the agent dir relative to this script so the launcher works no matter
# where it lives (Desktop, /Applications, inside an .app bundle, etc.).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -x "${SCRIPT_DIR}/.venv/bin/python" && -f "${SCRIPT_DIR}/serve.py" ]]; then
  AGENT_DIR="${SCRIPT_DIR}"
else
  AGENT_DIR="/Users/jeffleva/Dev/AI-Identity/agent"
fi
VENV_PY="${AGENT_DIR}/.venv/bin/python"

echo ""
echo "  ╭───────────────────────────────────╮"
echo "  │   Ada — AI Identity engineer       │"
echo "  ╰───────────────────────────────────╯"
echo ""

# Already running? Just open a tab.
if curl -fsS "${URL}/health" >/dev/null 2>&1; then
  echo "  ✓ Ada is already serving on ${URL}"
  echo "  → opening browser…"
  open "${URL}"
  echo ""
  echo "  This launcher window is safe to close."
  echo "  (The Ada server is running in another window.)"
  echo ""
  read -n 1 -s -r -p "  Press any key to exit. "
  echo ""
  exit 0
fi

if [[ ! -x "${VENV_PY}" ]]; then
  echo "  ✗ Couldn't find venv at ${VENV_PY}"
  echo "    Set it up with:"
  echo "      cd ${AGENT_DIR}"
  echo "      python3.11 -m venv .venv"
  echo "      .venv/bin/pip install -r requirements.txt"
  echo ""
  read -n 1 -s -r -p "  Press any key to exit. "
  exit 1
fi

cd "${AGENT_DIR}" || { echo "  ✗ cd failed"; exit 1; }

echo "  ▸ Starting Ada on ${URL}"
echo "  ▸ Logs stream below. Ctrl-C to stop."
echo ""

# Start serve.py in the background so we can wait for /health, then open browser.
"${VENV_PY}" serve.py --port "${PORT}" &
SERVE_PID=$!

# Make sure we kill the background process if this terminal window is closed.
trap 'echo ""; echo "  ▸ stopping Ada (pid ${SERVE_PID})…"; kill "${SERVE_PID}" 2>/dev/null; wait "${SERVE_PID}" 2>/dev/null; exit 0' INT TERM EXIT

# Poll /health for up to ~30 seconds.
for i in {1..60}; do
  if curl -fsS "${URL}/health" >/dev/null 2>&1; then
    echo ""
    echo "  ✓ Ada is up — opening browser…"
    open "${URL}"
    break
  fi
  sleep 0.5
done

# Hand the terminal to the server process so logs scroll and Ctrl-C works.
wait "${SERVE_PID}"
