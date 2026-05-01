#!/usr/bin/env bash
# Launch Ada — double-clickable Mac launcher.
#
# What it does:
#   1. git pull --ff-only origin main so merged PRs land on disk.
#   2. If Ada is already serving and its startup SHA matches HEAD, just open a
#      browser tab. If it's running on stale code, kill it and restart.
#   3. Otherwise: cd to the agent dir, activate the venv, start serve.py, wait
#      for /health to come up, then open the browser. Keeps this Terminal window
#      open so you can see logs and Ctrl-C to stop.
#
# Use directly by double-clicking, or via the wrapping `Launch Ada.app` built
# by `build_launcher.sh`.

set -u

# Don't block the launcher on a git credential prompt — if auth fails, fall
# through to "use on-disk code".
export GIT_TERMINAL_PROMPT=0

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

# Pull latest main so a fresh launch picks up merged PRs. --ff-only refuses to
# silently merge if the local checkout has diverged; print a warning and carry
# on with whatever's on disk in that case.
echo "  ▸ Pulling latest main…"
if git -C "${AGENT_DIR}" pull --ff-only origin main 2>&1 | sed 's/^/    /'; then
  HEAD_SHA="$(git -C "${AGENT_DIR}" rev-parse HEAD 2>/dev/null || echo unknown)"
else
  echo "  ⚠ git pull failed (diverged branch or offline?) — using on-disk code."
  HEAD_SHA="$(git -C "${AGENT_DIR}" rev-parse HEAD 2>/dev/null || echo unknown)"
fi
echo ""

# Already running? Compare the running server's startup SHA to current HEAD;
# if they match, just open a tab. If they differ (or /version is missing on an
# old server), the running process holds stale code — kill it and restart.
if curl -fsS "${URL}/health" >/dev/null 2>&1; then
  RUNNING_SHA="$(curl -fsS "${URL}/version" 2>/dev/null | sed -n 's/.*"sha":"\([^"]*\)".*/\1/p')"
  if [[ -n "${RUNNING_SHA}" && "${RUNNING_SHA}" == "${HEAD_SHA}" ]]; then
    echo "  ✓ Ada is already serving on ${URL} (sha ${RUNNING_SHA:0:8})"
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

  if [[ -z "${RUNNING_SHA}" ]]; then
    echo "  ▸ Running server has no /version endpoint — pre-version-check build. Restarting…"
  else
    echo "  ▸ Running server is on ${RUNNING_SHA:0:8}, HEAD is ${HEAD_SHA:0:8} — restarting…"
  fi
  STALE_PID="$(lsof -ti tcp:${PORT} 2>/dev/null | head -n 1 || true)"
  if [[ -n "${STALE_PID}" ]]; then
    kill "${STALE_PID}" 2>/dev/null || true
    # Wait for the port to free (up to ~5s).
    for _ in {1..10}; do
      curl -fsS "${URL}/health" >/dev/null 2>&1 || break
      sleep 0.5
    done
  fi
  echo ""
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
