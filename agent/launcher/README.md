# Ada launcher — macOS `.app` (menu-bar)

One-click launcher for Ada: a real macOS `.app` bundle with a custom icon that
lives in the menu bar, starts `serve.py`, polls `/healthz`, and shows a
status indicator.  No Terminal window; clean Quit stops the server.

## Architecture

```
Launch Ada.app/
  Contents/
    Info.plist           LSUIElement=true  → no Dock badge, no app switcher
    MacOS/launcher       tiny bash shim → exec venv python menubar_app.py
    Resources/
      ada.icns           app icon (for Finder)
      ada_menubar.png    22-pt @2x PNG for the status-bar icon
      menubar_app.py     bundled; owns serve.py as a subprocess

menubar_app.py
  ├── _find_agent_dir()    resolve agent/ at runtime (bundle-relative, then fallback)
  ├── ServerManager        subprocess.Popen(serve.py) + SIGTERM/SIGKILL lifecycle
  ├── _check_health()      polls http://127.0.0.1:8000/healthz every 5 s
  └── AdaMenuBar (rumps)   status-bar icon + menu callbacks
          ⏳  starting
          ✓   running
          ✗   stopped (auto-restarts serve.py)

serve.py (unchanged)
  └── uvicorn  FastAPI  ADK  →  http://127.0.0.1:8000
```

Logs stream to `~/Library/Logs/Ada/ada.log` (5 MB rotating, 3 backups).
`menubar_app.py` pipes `stdout` and `stderr` of `serve.py` there via daemon
threads, so all server output is captured even without a visible Terminal window.

## Build it

```bash
# Default: menu-bar .app (recommended)
bash agent/launcher/build_launcher.sh                  # → agent/dist/Launch Ada.app
bash agent/launcher/build_launcher.sh --install        # also copies to ~/Desktop

# Explicit flags (same result as above)
bash agent/launcher/build_launcher.sh --menubar
bash agent/launcher/build_launcher.sh --menubar --install
```

The script:
1. Regenerates `ada.icns` from `build_icon.py` if stale.
2. Auto-installs `rumps` and `Pillow` into the venv if missing
   (`agent/launcher/requirements.txt`).
3. Generates `ada_menubar.png` (44×44 @2x purple-A PNG for the status bar).
4. Writes `Info.plist` with `LSUIElement=true`.
5. Bundles `menubar_app.py` + icons into `Contents/Resources/`.
6. Writes `Contents/MacOS/launcher` shim that exec's venv python.

## Switching back to terminal mode

If you want the old behaviour (Terminal window pops up, logs stream visibly):

```bash
bash agent/launcher/build_launcher.sh --terminal-mode
bash agent/launcher/build_launcher.sh --terminal-mode --install
```

This builds the same `.app` shape but:
- `LSUIElement=false` (shows in Dock while Terminal is open).
- `MacOS/launcher` runs `open -a Terminal "agent/Launch Ada.command"`.
- `menubar_app.py` is **not** bundled.

You can also double-click `agent/Launch Ada.command` directly — it works
standalone (git pull, venv check, health poll, browser open) without any `.app`.

## Files

| File | Purpose |
|------|---------|
| `agent/launcher/menubar_app.py` | rumps menu-bar app; owns serve.py subprocess. |
| `agent/launcher/requirements.txt` | Launcher-only deps: `rumps`, `Pillow`. Not merged into `agent/requirements.txt`. |
| `agent/launcher/build_icon.py` | Renders the purple-A icon set → `ada.icns` via `iconutil`. |
| `agent/launcher/ada.icns` | Generated icon (committed for convenience). |
| `agent/launcher/ada_menubar.png` | Generated 44×44 @2x menu-bar icon (gitignored; regenerated on build). |
| `agent/launcher/build_launcher.sh` | Assembles `Launch Ada.app`; `--menubar` (default) or `--terminal-mode`. |
| `agent/Launch Ada.command` | Standalone terminal launcher (fallback; works without the .app). |

`agent/dist/` (the built `.app`) is gitignored.

## Menu structure

```
[◉ Ada]  ← status-bar icon (purple A) + status indicator
  Open Ada in browser      → open http://127.0.0.1:8000
  Show logs…               → open ~/Library/Logs/Ada/ada.log
  Restart server           → SIGTERM + relaunch serve.py
  ─────────────────────
  Quit Ada                 → graceful SIGTERM (5 s) → SIGKILL fallback → exit
```

## Log location

```
~/Library/Logs/Ada/ada.log
```

Open from the menu ("Show logs…"), from Console.app, or:

```bash
tail -f ~/Library/Logs/Ada/ada.log
```

The directory is created automatically on first launch.

## LSUIElement explained

`LSUIElement=true` in `Info.plist` tells macOS:

- Do **not** show an icon in the Dock.
- Do **not** include the app in Cmd-Tab app switcher.
- The app's only UI surface is the menu bar.

This is the standard setting for menu-bar utilities (e.g., Bartender, Lungo,
Stats). Without it, double-clicking the `.app` would show both a Dock badge
and a menu-bar icon, which looks wrong for a background service.

Terminal-mode builds set `LSUIElement=false` so the Terminal window (which is
the visible UI) behaves normally.

## Tweaking the icon

Edit colours / glyph in `build_icon.py`, then:

```bash
rm agent/launcher/ada.icns agent/launcher/ada_menubar.png 2>/dev/null || true
bash agent/launcher/build_launcher.sh --install
```

If macOS still shows a stale icon (LaunchServices cache):

```bash
sudo rm -rf /Library/Caches/com.apple.iconservices.store
killall Dock Finder
```

## Updating menubar_app.py

Unlike the terminal-mode shim, `menubar_app.py` **is** bundled into the `.app`.
Changes to the source file require a rebuild:

```bash
bash agent/launcher/build_launcher.sh --install
```

(The `.command` fallback still reads the live source file and needs no rebuild.)
