# Ada launcher — macOS `.app` icon

One-click launcher for Ada: a real macOS `.app` bundle with a custom icon
that pops a Terminal window, starts `serve.py`, polls `/health`, and opens
the chat UI in your browser.

If Ada is already running on `:8000`, double-clicking just opens a new
browser tab instead of crashing on a port conflict.

## Build it

```bash
bash agent/launcher/build_launcher.sh             # builds agent/dist/Launch Ada.app
bash agent/launcher/build_launcher.sh --install   # also copies to ~/Desktop
```

The script regenerates `ada.icns` from `build_icon.py` if it's missing or
older than the script. Pillow is auto-installed into the venv on first run.

## Files

| File | Purpose |
|------|---------|
| `agent/Launch Ada.command` | The actual launcher logic (also works double-clicked directly). |
| `agent/launcher/build_icon.py` | Renders a purple-A icon set and packs it into `ada.icns` via `iconutil`. |
| `agent/launcher/ada.icns` | Generated icon (committed for convenience — regenerate any time). |
| `agent/launcher/build_launcher.sh` | Assembles `Launch Ada.app/Contents/{Info.plist, MacOS/launcher, Resources/…}`. |

The built `.app` is gitignored under `agent/dist/`.

## How it works

`Launch Ada.app/Contents/MacOS/launcher` is a tiny shim that does:

```bash
open -a Terminal "/Users/jeffleva/Dev/AI-Identity/agent/Launch Ada.command"
```

The path to the source script is baked in at build time. The script itself
is **not** bundled — the .app delegates to the live file in the repo.

That means: edit `agent/Launch Ada.command`, save, double-click the .app —
done. No rebuild. The .app is a stable shell; the launcher logic lives in
the repo where you can change it freely.

You only need to rebuild the .app when:

- The icon changes (`build_icon.py` edited).
- `Info.plist` (bundle ID, version, display name) changes.
- The shim itself changes (i.e., what the .app does *before* opening Terminal).

If you move or rename the repo, the shim's hardcoded source path will break;
the .app will pop a dialog telling you to re-run `build_launcher.sh`.

## Tweaking the icon

Edit colors / glyph in `build_icon.py`, then:

```bash
rm agent/launcher/ada.icns
bash agent/launcher/build_launcher.sh --install
```

The `touch` at the end of the build forces Finder to re-read the icon. If
macOS still shows a stale icon (LaunchServices cache), log out and back in,
or run:

```bash
sudo rm -rf /Library/Caches/com.apple.iconservices.store
killall Dock Finder
```
