# CoSAI WS4 shared docs — collaboration + sync workflow

These two docs are **co-edited** (Teryl/IBM on the OCSF issues draft; the whole
WS4 group on the interop map), so the live editing surface is **Google Docs**,
and git holds a **one-directional markdown snapshot** for version history and as
the text we paste into GitHub issues when filing.

| Doc | Canonical (edit here) | Git snapshot |
|---|---|---|
| OCSF Issues — Working Draft | Google Doc (shared w/ Teryl, Fred) | `docs/cosai-ws4-ocsf-mapping/ocsf-issues-draft-with-teryl.md` |
| CoSAI WS4 Interop Map | Google Doc (shared w/ WS4) | `docs/strategy/cosai-ws4-interop-map.md` |

## The rules that prevent drift

1. **One canonical Google Doc per doc.** Edit there, live, with collaborators.
2. **Never edit a downloaded copy.** Downloading a `.docx`/`.pages` to edit is
   exactly what caused the June 2026 drift — multiple divergent copies. Git only
   ever *reads* from the Google Doc; it never writes back.
3. **Sync is one-directional** (Google Doc → git), run at checkpoints: before a
   WG call, and before filing any section as a GitHub issue.
4. **Internal reviewer notes never go in the Google Doc** (collaborators see it).
   They live only in git, in a sibling `*.notes.md` file that sync never
   overwrites.

## Syncing (two ways)

**A. Claude-driven (preferred, once the Google Drive connector is connected).**
Ask: *"sync the cosai docs."* Claude exports each Google Doc, converts via
pandoc, updates the snapshot `.md`, and opens a commit/PR. No local auth setup.

**B. Manual fallback (works today).** In each Google Doc: `File → Download →
Microsoft Word (.docx)`, then:

```bash
scripts/cosai-docs/sync.sh ~/Downloads/<exported>.docx docs/<path>/<target>.md
# review the diff, then:
git add docs/<path>/<target>.md && git commit
```

The snapshot `.md` is a faithful archive — readable and diffable, but not
pixel-perfect markdown. Polish (heading levels, fenced JSON, clean tables)
happens only when a section is filed as a GitHub issue, not on every sync.

## One-time setup

1. Upload the two current `.docx` (in `~/Downloads/…-resynced.docx`) to Google
   Drive and open each as a Google Doc (Drive converts and preserves
   headings/tables). These become the canonical docs.
2. Share each with the collaborators (Teryl/Fred for the issues draft; the WS4
   group for the interop map), edit access.
3. **Archive the stray copies** — the older `.pages`/`.docx` in `Downloads/` and
   `Documents/` — so there's exactly one canonical surface.
4. Connect the Google Drive connector in Claude to enable workflow A.
