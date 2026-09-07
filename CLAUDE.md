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
