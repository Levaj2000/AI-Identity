# CLAUDE.md

Guidance for Claude Code working in this repository.

Engineering conventions live in [AGENTS.md](AGENTS.md). Read that first; it governs
definition-of-done, test commands, PR workflow, and what to hand back rather than own.
This file carries conventions specific to how Claude writes and hands over work.

## Plain ASCII in anything that leaves the session

The maintainer's terminal and downstream tooling mangle non-ASCII punctuation. Anything
Claude produces that will be pasted, piped, or posted must be plain ASCII.

Specifically, do not use:

- Em dashes or en dashes. Use a comma, a colon, a semicolon, or a full stop instead.
- Curly quotes and curly apostrophes. Use the straight ' and " characters.
- The ellipsis character, arrows, non-breaking spaces, or other typographic symbols.
  Spell them out or restructure the sentence.

This applies to shell commands and heredocs, GitHub issue and PR bodies, commit messages,
email drafts, and any file written for the maintainer to copy or send. It applies to
generated content too, not just prose: a table or code comment is no exception.

Verify before handing anything over:

```bash
LC_ALL=C grep -n '[^[:print:][:space:]]' <file>
```

Zero output means the file is clean. For a count across several files:

```bash
LC_ALL=C grep -o '[^[:print:][:space:]]' <file> | wc -l
```

## Outreach and relationship records stay out of this repository

This repository is public. Named contacts, email addresses, and verbatim outreach drafts
do not belong in it; see `docs/security/public-repo-exposure-remediation.md` for the audit
that removed an earlier set of them. Records like these belong in the maintainer's Notion
workspace, in the Outreach Log for external relationships or CoSAI Follow-ups for standards
commitments.

## Work the maintainer posts himself: write the command so it cannot miss

`AGENTS.md`, "Batch Delivery for Work the User Posts Manually", is the protocol.
Read it before preparing anything destined for a repo the maintainer does not own
(OCSF, CoSAI, collaborators' repos). This section is the enforcement note, added
after all three of its rules were broken inside a single session.

**Default to a heredoc that writes the file, not to a file he has to find.**
Sending a file and then naming it in a command couples that command to a filename
his browser has already altered: downloads arrive with hyphens stripped, so
`pr181-reply.md` lands as `pr181reply.md` and the command fails with "no such file".
A single paste-able block that writes the content and then acts on it has no
filename dependency at all:

```bash
cat > ~/thing.md <<'THING_EOF'
...content...
THING_EOF

gh pr comment 123 --repo owner/repo --body-file ~/thing.md
```

Quote the heredoc delimiter so backticks, `#` and `$` reach the file literally,
and give the file a name with no hyphens. Send the artifact as a file too when it
is worth reading on its own, but never let the command depend on where it landed.

**Never put a value in a command block that he has to replace by hand.** No
`<placeholder>`, no `#NNNN`, no `# comment` lines: the shell executes them
literally and he pastes whole blocks. When a value only exists after an earlier
step (an issue number, a SHA, a gist URL), capture it into a variable in the same
block, or split into two blocks so the first prints the value the second consumes.
Ordering matters as much as syntax: a command that references the result of a step
he has not run yet will run anyway and post the placeholder. That has happened, in
public, on a standards thread.

**Never put `set -e` at the top level of a block he pastes into an interactive
shell.** In interactive zsh, `set -e` persists after the block, and the first
failing command exits the whole shell: Terminal prints "[Process completed]" and
the window is gone, along with any output he had not yet copied. That is what a
guard is supposed to do, stop the block, but it must not take the terminal with
it. Wrap the block in a subshell so the option dies with it, or chain the steps
with `&&` so a failure stops the block and returns him to the prompt:

```bash
(
set -e
cd ~/thing
git fetch origin main
git reset --hard origin/main
)
```

Either shape returns him to a working prompt on failure. A guard that stops a
block is a feature; a guard that closes the terminal happened on 2026-09-08 and
cost a re-run from a fresh window.

**State the routing split before starting.** Name which actions land directly from
the session and which he has to run himself, at the top of the task, not at the
point where the first command fails.

**No Claude identity on a commit bound for a repo with a CLA.** CoSAI and OCSF run
CLA Assistant, which resolves every commit author to a GitHub account and blocks
the merge until each one has signed. Claude cannot sign, so a commit it authors
turns the check red and the maintainer has to amend and force-push under his own
ID; that happened on ws4 PR #181. Observed on the same PR: a `Co-Authored-By`
trailer alone did not trip the check, but keep trailers off those commits anyway,
since the CLA bot's co-author handling is a setting the repo owner can change. The attribution trailers this harness adds by default are for this
repository only. For a change he will commit elsewhere, hand him the file content
or a patch, and write the commit step with his author string and no trailers:

```bash
git commit --author='Jeff Leva <120221487+Levaj2000@users.noreply.github.com>' -F ~/msg.txt
```
