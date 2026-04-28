# Discovery → Scoping Playbook

Practical workflow for executing **Step 1 (Discovery call)** and **Step 2 (Scoping doc)**
of the founding-partner engagement process.

Designed for a solo founder. Templates are **Word docs** (.docx) — what you
actually send to a Security Director or attach in an email. Claude Code helps
draft them from raw call notes when that's faster than filling them in by hand.

## Folder layout

```
marketing/sales/
├── playbook/
│   ├── README.md                                ← this file
│   ├── build-docx.sh                            ← markdown → Word converter (uses pandoc)
│   ├── templates/
│   │   ├── pre-call-intake.docx                 ← email this Day 0
│   │   ├── discovery-summary-template.docx      ← Step 1 deliverable (Word)
│   │   ├── scoping-doc-template.docx            ← Step 2 deliverable (Word)
│   │   └── *.md                                 ← markdown sources (regenerate .docx if you edit)
│   └── prompts/
│       ├── synthesize-summary.md                ← Claude prompt for the Step 1 draft
│       └── draft-scoping.md                     ← Claude prompt for the Step 2 draft
└── engagements/
    └── <customer-slug>/                         ← one folder per prospect
        ├── inputs/
        │   ├── agent-inventory.csv              ← what they send you
        │   └── call-notes.md                    ← what you write live
        ├── 01-discovery-summary.docx            ← what gets emailed to the prospect
        └── 02-scoping-doc.docx                  ← what becomes the soft contract
```

## Two ways to use the templates

You have two paths depending on what's easier for the call you just finished.

### Path A — Fill the Word template directly (10-30 min)

Best for short discovery calls where you have a clean read on what the
prospect needs and you don't have a ton of notes to wrangle.

1. **Copy the Word template** into the engagement folder:
   ```bash
   cp playbook/templates/discovery-summary-template.docx \
      engagements/standard-motor/01-discovery-summary.docx
   ```
2. **Open it in Pages or Word.** Replace every `{{ ... }}` placeholder with
   the real content from your call.
3. **Save and email it.** No conversion step.

### Path B — Have Claude draft it from notes (45 min, more thorough)

Best when the call ran long, the prospect's situation is complex, or you
want a structured summary surfaced from messy notes.

1. **Capture call notes** in `engagements/<slug>/inputs/call-notes.md` —
   markdown is fine here because nobody but you and Claude will read it.
   Don't worry about structure; capture content.
2. **Drop any agent inventory** the prospect sent into
   `inputs/agent-inventory.csv` (or whatever format they used).
3. **In Claude Code**, with the engagement folder as your working directory:

   > Follow `playbook/prompts/synthesize-summary.md` against the inputs
   > here. Output to `01-discovery-summary.md`.

4. **Review the markdown draft.** Especially the "Where AI Identity does
   NOT fit" section — this is where Claude will soften when you don't want
   it to.
5. **Convert to Word** with the helper script:
   ```bash
   ./playbook/build-docx.sh engagements/standard-motor/01-discovery-summary.md
   ```
   This produces `01-discovery-summary.docx` in the same folder.
6. **Open in Pages/Word, polish, send.**

## Same workflow for the scoping doc

Step 2 mirrors Step 1 — pick Path A or B based on the prospect's complexity.

- **Path A**: copy `scoping-doc-template.docx` into the engagement folder,
  fill it in by hand.
- **Path B**: drop any follow-up notes into `inputs/scoping-followup.md`,
  run the `draft-scoping.md` Claude prompt, convert to .docx with the helper.

The scoping doc is more important to send as a Word doc than the discovery
summary, because procurement / legal will want to redline it. A Google Doc
also works if your prospect prefers commenting in Google Workspace.

## What the Day-0 intake looks like in practice

The pre-call intake (`pre-call-intake.docx`) is meant to be the *body* of an
email — not a separate attachment. Easiest workflow:

1. Open `pre-call-intake.docx` in Pages.
2. Replace `{{ name }}` and `{{ day }}`.
3. Copy-paste the body into your email client.
4. Send. The prospect replies inline with whatever's easy.

If you'd rather send it as an attachment, just attach the .docx — but inline
text gets a higher response rate.

## What Claude is good at, what you're good at

| Task | Owner |
|---|---|
| Structure (sections, headings, consistency) | Claude |
| Pulling specific risks from messy notes | Claude |
| Drafting policy descriptions in technical language | Claude |
| Detecting when AI Identity is a poor fit and saying so | **You** |
| Calibrating what's promiseable in 90 days | **You** |
| Voice and tone (matching the rest of your customer-facing material) | Mostly Claude, with edits |
| The "what we won't do" section | **You** — Claude will skip this if you don't push |

## Time budget per prospect

- Day 0 intake email: 5 min
- Discovery call: 60 min
- Discovery summary (Path A or B): 30-45 min
- Scoping doc (Path A or B): 45-60 min
- **Total founder time over 5 days: 2.5-3 hours**

Don't take a fifth prospect through the funnel until the first four are at
decision points.

## Worked example

The `engagements/standard-motor/` folder is pre-scaffolded for the Kevin
Pentecost meeting on Tuesday. After the call:

- **Path A**: copy `playbook/templates/discovery-summary-template.docx` to
  `engagements/standard-motor/01-discovery-summary.docx`, open in Pages,
  fill in.
- **Path B**: dump notes into `engagements/standard-motor/inputs/call-notes.md`,
  run the synthesize prompt, then run `./playbook/build-docx.sh` on the
  output.

## Why .docx and not .md for the deliverables

Markdown is great for engineers and great for me (Claude) to read and write.
It's not what a Security Director forwards to procurement. The deliverables
that go to prospects need to be Word docs:

- **Editable** — procurement / legal can redline directly.
- **Universally readable** — Pages, Word, Google Docs, LibreOffice all open .docx.
- **Familiar formatting** — bullets, headings, tables render the way the
  prospect expects without their email client trying to parse markdown
  syntax.
- **Convertible to PDF in one click** — File → Export as PDF in Pages.

The internal artifacts — Claude prompts, this README, your own call notes
— stay markdown. Those are tools, not deliverables.
