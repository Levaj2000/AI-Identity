# Public-repo exposure audit and remediation

**Date:** 2026-07-26
**Scope:** `github.com/Levaj2000/AI-Identity` — a **public** repository
**Trigger:** "How much can someone learn about my work from reviewing my public GitHub repository?"

---

## Summary

No credentials were exposed. All 1,113 blobs in the full git history were
scanned for API keys, private keys, database URLs, and cloud tokens; every hit
was a test fixture or placeholder. Secrets live in Google Secret Manager and
are referenced by name only. The only committed key material is
`docs/cosai-ws4-ocsf-mapping/attestation-finding-sample/checkpoint-public-key.pem`,
a public key published on purpose.

The exposure was **commercial, not technical**: the business was in the repo
alongside the code.

---

## What was removed

| Path | Why |
|---|---|
| `marketing/sales/pipeline-snapshots/` | Live CRM export — named prospects, named contacts, candid internal deal risk ("overstates readiness", "cannot count toward H1 gate") |
| `marketing/sales/engagements/` | Per-account working folder naming a prospect's Security Director |
| `marketing/sales/` (decks, playbook, pricing, discovery, briefings) | Pricing sheets and account-specific collateral |
| `outreach/design-partner-messages.md` | Eight target companies with named CEOs, verified email addresses, verbatim cold-email drafts, and the day-5/12/21 follow-up cadence — readable by the recipients |
| `competitive-brief-april-2026.md` | 28KB teardown of four named competitors, including where we believe we are threatened |
| `AI_Identity_Budget_Tracker.xlsx` | Vendor spend, payment method ("Visa ending 3326"), and three unrelated side projects |
| `AI-Identity-Status-Report-2026-04-06.docx` | Weekly metrics against internal targets |

**Scope note:** the original recommendation said "move `marketing/`". Only
`marketing/sales/` was removed. The rest — `blog/`, `buttondown/`, `linkedin/`,
`whitepapers/`, `campaign-launch/`, `partner/` — is published or publishable
collateral with no third-party confidential data, and four build scripts depend
on those paths. To remove it anyway:

```bash
git rm -r marketing/blog marketing/buttondown marketing/linkedin \
          marketing/whitepapers marketing/campaign-launch marketing/partner
# then fix: scripts/render_whitepaper_pdf.py, scripts/forensics-kb/stage_corpus.py,
#           docs/forensics/build_evidence_anchor_notes_pdf.py
```

## What stays public, deliberately

These were found and judged worth keeping. Flagging them so the choice is
explicit rather than accidental:

- **`docs/incidents/2026-04-16-audit-infrastructure.md`** — a P0 write-up
  stating that audit logging was down for ~72 hours, on the product's core
  compliance claim. Publishing it is a defensible trust position, but it is
  the single most quotable document against us in a competitive deal.
- **`docs/compliance/`** — access-management, change-management, and
  incident-response policies. Useful to buyers; also a map of our controls.
- **Infrastructure identifiers** — GCP project `project-8bbb04f8-…` (249
  occurrences), service-account addresses, GitHub secret *names*. Not secrets,
  and no keys leaked, but they map the blast radius precisely.
- **`docs/strategy/`** — roadmap to 2030, R&D landscape reports, CoSAI WS4
  work naming external IBM collaborators.
- **Full product source** — `LICENSE` declares a proprietary core, but
  proprietary is not private. The gateway enforcement logic, policy engine,
  and audit chain are readable and copyable.
- **Root-level company collateral** — `AI-IDENTITY-SUMMARY.md` (market,
  buyers, competitive landscape, near/mid/long-term plans),
  `AI-Agent-Lifecycle-Training.pptx`, `5-signs-audit-ready-carousel.pdf`.
  These read as an intentional public pitch and the carousel was published on
  LinkedIn anyway. Worth a second look if the plans section is more forward-
  looking than you want competitors reading.

## Personal data

Two personal Gmail addresses were published across 8 occurrences — the
founder's (7) and one other person's (1) — harvestable for targeted phishing.
They are deliberately not reproduced in this document; see the SHA-256 values
in `common/queries/user_cleanup.py` if you need to confirm a match.

`common/queries/user_cleanup.py` hardcoded both in `PROTECTED_EMAILS`, the
allowlist that stops the weekly cleanup cron from deleting those accounts.
Removing them naively would have made the accounts deletable, so protection is
now two-layered:

1. `PROTECTED_EMAILS` — read from the `PROTECTED_EMAILS` env var
   (comma-separated). Extends the list without a deploy, and lets callers push
   the exclusion into SQL.
2. `_PROTECTED_EMAIL_HASHES` — a hard-coded SHA-256 backstop. **An unset env
   var must never mean "protect nobody."**

`is_protected()` checks both and is authoritative; it is case-insensitive and
whitespace-tolerant, so it is strictly more protective than the previous set
membership test. Every deletion path (`cleanup_cron.py`, `purge_test_users.py`,
`delete_users_with_cascade`) filters through it. The SQL `notin_` is now a
pre-filter applied only when the env var is populated.

To configure:

```bash
gcloud secrets versions add ai-identity-PROTECTED_EMAILS --data-file=-
# value: comma-separated addresses
```

## The republishing loop (the part that mattered most)

`.github/workflows/ceo-dashboard-sync.yml` ran every Monday at 14:00 UTC with
`contents: write`, regenerating the pipeline CSV and **committing it back to
the public repo**. Deleting the CSV alone would have republished it the
following Monday.

The commit step and the `contents: write` permission are removed. The briefing
posted to the CEO dashboard is the real delivery mechanism; the CSV now writes
to the gitignored `private/` tree and is discarded with the runner. It is
deliberately **not** uploaded as an Actions artifact — artifacts on a public
repo are downloadable by anyone.

`scripts/export_pipeline_snapshot.py` writes to `private/pipeline-snapshots/`,
overridable via `PIPELINE_SNAPSHOT_DIR` (point it outside the repo entirely if
you prefer). `docs/strategy/build_anthropic_tier_posture_pdf.py` writes to
`private/sales/`.

## Guards

- `.gitignore` — `private/`, `marketing/sales/`, `outreach/`,
  `competitive-brief-*.md`, `*Budget_Tracker*.xlsx`,
  `AI-Identity-Status-Report-*.docx`, following the existing "this repo is
  PUBLIC — NEVER COMMIT" convention.
- `scripts/check-no-confidential.sh` — pre-commit hook, the second line of
  defence since `.gitignore` is bypassed by `git add -f`. Inspects **staged**
  content and fails the commit on forbidden paths or forbidden personal
  addresses. Addresses are matched by SHA-256 so the guard does not itself
  leak them.

## Removing this from history

**Deleting a file in a normal commit does not unpublish it.** Every removed
file is still reachable in history and through the GitHub UI. Run:

```bash
git clone https://github.com/Levaj2000/AI-Identity.git ai-identity-scrub
cd ai-identity-scrub
pip install git-filter-repo
./scripts/scrub-public-history.sh
```

The script exports the material to `../ai-identity-private-export/` **before**
destroying it, refuses to proceed if that export is empty, rewrites history,
and verifies the blobs are gone. Force-pushing is left to you.

### Residual risk after the rewrite

A history rewrite is not an unpublish. Assume the pipeline CSV and outreach
list have already been read, indexed, or forked:

- Old commits stay reachable by direct SHA URL until GitHub garbage-collects
  them. Open a Support request to purge cached views.
- Check for forks first: `/network/members`. A fork retains everything.
- Pull requests that referenced the old SHAs keep them.
- No credentials leaked, so there is nothing to rotate — but do not treat the
  rewrite as making the content secret again.
