# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## What This Repository Is

The public trust surface of AI Identity: the offline verifier CLI, the SDKs, the
CPEX OCSF audit plugin, the OCSF and CoSAI mapping documents, the OTel crosswalk,
the evidence-anchor trust model, and the public website. The platform (API server,
gateway, mandate service, dashboard, deployment) lives in a private repository.
Do not add platform code here, and do not reach for platform modules that no
longer exist in this tree: if a task needs them, it belongs in the platform repo.

## Working as a Delegated / Offload Agent

Tasks are often delegated here to run autonomously. Own the task end-to-end to the same bar as a clean handoff: a root-cause fix, tests, a fully green suite, and a tight diff.

**Definition of done — all of these, in order:**
1. **Plan first.** State the root cause and intended change before editing. For anything past a one-line fix, outline the approach.
2. **Fix the cause, not the symptom.** Prefer the defensive/correct fix over a patch that just silences the error.
3. **Add or update tests** that would have caught the bug. New behavior without a test is not done.
4. **Run the full suite and quote summaries verbatim.** `ruff check .`, `ruff format --check .`, and `pytest -v` from the repo root (the verifier CLI suite). For landing-page changes, `cd landing-page && npx tsc --noEmit && npx next build`. Report passes and skips separately (see "Verification Before Reporting Done").
5. **Keep the diff tight.** Touch only what the task needs. Don't refactor adjacent code, reformat unrelated lines, or "improve" things unasked — surface those as a note instead.
6. **Report with evidence** — quoted test summaries, files changed, what was verified. No "should work."

**Stop and hand back (do NOT autonomously merge) when the task touches:**
- **OCSF / standards work** — schema files, `attestation.json`, profiles, anything feeding upstream OCSF or CoSAI PRs. Public-facing and reputation-bearing; facts and framing need a human pass.
- **The evidence-anchor mirror** — `.github/workflows/evidence-anchor-mirror.yml`, `scripts/evidence_anchor_mirror.py`, or anything on the `evidence-anchor-mirror` branch. That branch is the public witness; its value is that it has never been rewritten.
- **Verifier semantics** — any change to what `cli/ai_identity_verify.py` accepts or rejects. Relying parties depend on it.
- **Public-facing copy** — landing-page/marketing/docs claims (the "Four Pillars", no-vaporware code-state claims).
- **Ambiguous scope** — if the task could mean two things, ask rather than guess.

Green to fully own: bugfixes with a clear repro, test/coverage additions, mechanical refactors within a file, dependency-level fixes — anything where a passing full suite is sufficient proof.

## This Repo Is Public — Drafts and Prep Are Never Committed

Everything tracked here is world-readable. Two consequences:

- **Reply/comment drafts, outreach prep, strategy notes, and reviewer notes about named people do NOT get committed.** Deliver draft replies in chat, or write them to `private/` (gitignored). This applies to Slack replies, GitHub comment drafts, issue-filing prep, and any `*.notes.md`. `docs/` is only for artifacts meant to be linked publicly (reference bundles, class drafts, the crosswalk, specs).
- **CHANGELOG entries describe what shipped, not why strategically.** No negotiation posture, no notes about collaborators' access or availability, no "the play here is…" framing — that context goes in `private/` session notes.

## Batch Delivery for Work the User Posts Manually (Jeff's protocol, 2026-08-25)

Sessions here are scoped to this repo only — cross-owner attach is refused, so
anything destined for a repo Jeff doesn't own (OCSF, CoSAI, collaborators'
repos) is posted by Jeff from his own terminal with `gh`. When preparing that
kind of work, deliver in ONE batch, not a drip:

- **All files at once.** Every artifact the task needs (comment bodies, patches,
  fixtures, keys) in a single send — never referenced before delivered. Jeff's
  browser strips hyphens from downloaded filenames, so commands must never
  hard-code a name: find files with a pattern (`ls -t ~/Downloads/<glob> | head -1`)
  or tell him to tab-complete.
- **One paste-able script**, not sequential commands with narration between
  them. No `# comments` or `<placeholders>` inside command blocks — his shell
  executes both literally. Values discovered mid-flow (a gist URL, a SHA) get a
  `sed` step in the script, not a hand-edit instruction.
- **State the routing split up front.** At the start of any task touching
  repos beyond this one, say which actions land directly from the session and
  which route through Jeff, before starting either.
- Author commits he will push as `Jeff Leva
  <120221487+Levaj2000@users.noreply.github.com>` — his account blocks pushes
  exposing the private address (GH007).
- **No Claude identity anywhere in a commit bound for CoSAI or OCSF**: not as
  author, not as committer, and not in a `Co-Authored-By` or `Claude-Session`
  trailer. Those repos gate merges on a CLA that resolves every commit identity
  to a GitHub account, and Claude cannot sign one. A commit authored by Claude
  on ws4 PR #181 (2026-09-08) turned the CLA check red and had to be amended and
  force-pushed under Jeff's ID. Deliver the change as a patch or a heredoc he
  commits himself with `--author` set as above and no trailers.

## Verification Before Reporting Done

Never claim "tests pass" without running pytest and quoting its summary line verbatim (e.g. `===== 39 passed in 5.91s =====`). If tests cannot be executed in the current environment, say so — do not substitute static review for actual execution. Line counts (`wc -l`) and test counts (`pytest --collect-only -q | tail -1`) are different numbers; quote the pytest one.

Skipped tests are not passing tests. Report `57 passed, 6 skipped` separately — never roll skips into the green count. Tests that depend on env vars should set them via `monkeypatch` or `conftest.py`, not gate themselves with `pytest.skip("X not configured")`. A skip-on-missing-env pattern silently disables coverage exactly where it's most needed.

## Brand Consistency (Enforced by Pre-commit)

The "Four Pillars" (Identity → Policy → Compliance → Forensics) is canonical. Never write "three pillars". The pre-commit hook `scripts/check-pillar-consistency.sh` enforces this in `landing-page/`, `docs/`, and `marketing/` directories.

## Code Style (Ruff)

- Line length: 100 (not 88)
- Ignores: `E501` (line too long, handled by formatter)
- CLI targets Python 3.9+, so `datetime.UTC` is forbidden there (use `datetime.now(UTC)` instead)

## Ruff Format: Double Quotes

`[tool.ruff.format] quote-style = "double"` — auto-fixers that prefer single quotes will fight the formatter. Configure your editor accordingly.

## PR Workflow

Per `CONTRIBUTING.md`: open an issue first, wait for a maintainer to assign it, then branch from `main`. Don't open speculative PRs without a tracked issue.

PRs target `main` by default. Do not ask "which branch should this merge into" as a routine question — the answer is `main` for any completed work. Only ask if the user has explicitly signaled a stacked-PR workflow (e.g. "build on top of PR #X", "this depends on the unmerged `feat/Y` branch") or if the change is genuinely a fix to an unmerged feature branch rather than a new contribution. Default behavior: branch off `main`, target `main`, merge to `main`.

**Squash merges carry the trailers forward.** GitHub credits the PR author when a PR holds commits from more than one author, and a hand-written squash body drops whatever trailers the individual commits carried. Both together erase the real provenance: #497 is the case — a session regenerated the lockfile and changed `src/sign.rs`, and the squash landed the lot as `renovate[bot]` with no `Co-Authored-By` at all, so `git blame` on `fingerprint_value` now names a bot that cannot write Rust. When writing a squash body, copy every distinct `Co-Authored-By` (and the `Claude-Session` line, where one is present) from the commits being squashed into it. The PR keeps the true history either way, but `git blame` only sees the squash.

## Private Strategy Documents Live in Notion, Not Here

Private strategy and relationship documents (commercial planning, partner
memos, anything marked PRIVATE) are maintained in the owner's Notion
workspace — that is their canonical home. **Never commit them to this
repository**, including under a `private/` directory, and never quote their
contents into public artifacts, PR bodies, or issue comments. When revising
one, update its Notion page rather than creating a repo file; a file handed
around in chat is an export, not the document. The public-repo CI gate
("no confidential material") is a backstop, not the policy.
