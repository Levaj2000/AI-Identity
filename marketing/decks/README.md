# Decks

## DenAI Summit 2026 — Startup Showcase (v4)

`AI-Identity-DenAI-Showcase-2026-v4.pptx` — 8 slides, scripted for the showcase's
4–5 minute stage slot. Every slide carries timed speaker notes.

| # | Slide | Beat |
|---|---|---|
| 1 | Cover + one signed record | 0:00–0:20 |
| 2 | The $40,000 at 2 a.m. — identity / authority / evidence | 0:20–1:00 |
| 3 | The control path, and what it does not replace | 1:00–1:45 |
| 4 | Procurement agent under a $5,000 delegated limit | 1:45–3:00 |
| 5 | Three city workflows + how it deploys | 3:00–3:30 |
| 6 | OCSF 1.9 and vendor-neutral verification | 3:30–4:15 |
| 7 | The pilot ask + Colorado anchor | 4:15–4:40 |
| 8 | Founder and close | 4:40–5:00 |

### Before submitting or presenting

Slide 7 carries a deliberate amber placeholder card, `[ REPLACE THIS CARD ]`.
Fill in the Colorado agency, the person who owns the workflow, and the workflow
itself. The showcase selects Colorado companies building for cities, so a named
local workflow is the highest-value edit in the deck.

The `$5,000` delegated limit and the four decisions on slide 4 describe the
reference demonstration, not a production deployment at a named city. Keep that
framing accurate if the numbers change.

### Rebuilding

```bash
npm install pptxgenjs
node denai-showcase-2026-v4.build.js
```

Changes go in the generator, not the packed `.pptx`.

### QA

`pptx_qa.py` checks geometry and text fit, and renders an approximation of each
slide to `slide-N.png`:

```bash
pip install python-pptx Pillow
python3 pptx_qa.py AI-Identity-DenAI-Showcase-2026-v4.pptx
```

It exists because LibreOffice Impress is not always available to convert the
deck to PDF. It redraws the real package with metric-compatible font
substitutes (Calibri → Liberation Sans, Cambria → Liberation Serif × 1.08,
Courier New → Liberation Mono), so overflow warnings are conservative rather
than optimistic. It approximates: use PowerPoint or LibreOffice for a faithful
render before presenting.
