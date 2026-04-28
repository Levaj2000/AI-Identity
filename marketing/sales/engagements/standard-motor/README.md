# Standard Motor Co — engagement folder

**Prospect:** Standard Motor Products
**Primary contact:** Kevin Pentecost (Security Director)
**Discovery call:** April 28, 2026
**Owner:** Jeff Leva

## After the discovery call — pick a path

### Path A: Fill the Word template by hand (10-30 min, fastest)

```bash
cp ../../playbook/templates/discovery-summary-template.docx \
   01-discovery-summary.docx
```

Then open `01-discovery-summary.docx` in Pages or Word, replace each
`{{ placeholder }}` with content from the call, save, send.

### Path B: Have Claude draft it from notes (45 min, more thorough)

1. Drop your call notes into [inputs/call-notes.md](inputs/call-notes.md)
   (overwrite the placeholder).
2. If Kevin sent an agent inventory, save it to `inputs/agent-inventory.csv`
   (or `.md`, `.xlsx`, whatever format he sent).
3. Open Claude Code with this folder as the working directory.
4. Tell Claude:

   > Follow `../../playbook/prompts/synthesize-summary.md` against the
   > inputs here. Output to `01-discovery-summary.md`.

5. Review the markdown draft — especially the "Where AI Identity does NOT
   fit" section.
6. Convert to Word:

   ```bash
   ../../playbook/build-docx.sh 01-discovery-summary.md
   ```

7. Open `01-discovery-summary.docx` in Pages, polish, send.

## Days 3-5: scoping doc

Same two paths. For Kevin, **Path B is recommended** for the scoping doc
because the agent inventory and risk discussion will probably need
structured synthesis.

1. Save any of Kevin's reply / follow-up info to `inputs/scoping-followup.md`.
2. Tell Claude:

   > Follow `../../playbook/prompts/draft-scoping.md`. Inputs: this folder
   > plus `01-discovery-summary.md` (or `.docx` if that's what you have).
   > Output to `02-scoping-doc.md`.

3. Review carefully — the day-90 success criteria must be SMART.
4. Convert to Word:

   ```bash
   ../../playbook/build-docx.sh 02-scoping-doc.md
   ```

5. Send `02-scoping-doc.docx` as a Word attachment, OR upload to Google Docs
   and share the link if Kevin's team prefers commenting in Google Workspace.

## Reference materials for tomorrow

| File | Purpose |
|---|---|
| `../../briefing-standard-motor-2026-04-28.pptx` | Your meeting deck |
| `../../info-deck-standard-motor-2026-04-28.pptx` | Leave-behind for Kevin |
| `../../pricing-sheet-2026-04-27-v2.pdf` | Pricing sheet (PDF) |
| `../../playbook/templates/pre-call-intake.docx` | Pre-call email body (already late, but useful for next prospect) |
