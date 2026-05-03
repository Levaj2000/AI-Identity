"""Citation extraction + verification for Ada's responses.

Two checks per cited ``path:line``:

1. **Real** — the path exists in the workspace and the line is within the
   file's line count. Catches hallucinated files and out-of-range line
   numbers (the most common citation-fabrication failure mode logged
   through the May 1 dogfood session).

2. **Grounded** — the path appeared in *some* tool response this turn.
   Catches the case where Ada cites a file she never read or searched.

Pure functions, no ADK dependency. Used by the static eval harness today
and (planned) as an ADK ``after_model_callback`` to self-verify Ada's
responses before they reach the user.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Match `path/to/file.ext:lineno` and `path/to/file.ext:start-end`. The
# `\.[A-Za-z0-9]+:` shape avoids time strings (`12:34`) — we require a
# file extension immediately before the colon. URLs are stripped from
# input before extraction (see :func:`extract_citations`); without that
# pass, hostnames like `gateway.ai-identity.co:443` would match because
# `co` is a valid extension shape.
_CITATION_RE = re.compile(
    r"(?<![A-Za-z0-9_/-])([A-Za-z0-9_./-]+\.[A-Za-z0-9]+):(\d+)(?:-(\d+))?",
)
_URL_RE = re.compile(r"https?://\S+")


@dataclass(frozen=True)
class Citation:
    """One ``path:line`` (or ``path:start-end``) reference extracted from text."""

    path: str
    start_line: int
    end_line: int  # equals start_line for single-line citations
    raw: str


@dataclass(frozen=True)
class CitationCheckResult:
    """Outcome of verifying one :class:`Citation`."""

    citation: Citation
    real: bool
    grounded: bool
    reason: str | None = None

    @property
    def passed(self) -> bool:
        return self.real and self.grounded


def extract_citations(text: str) -> list[Citation]:
    """Return every ``path:line`` (or ``path:start-end``) in ``text``.

    URLs (``http(s)://...``) are stripped from ``text`` before scanning so
    hostnames like ``gateway.ai-identity.co:443`` aren't mis-extracted as
    citations.
    """
    cleaned = _URL_RE.sub("", text)
    out: list[Citation] = []
    for match in _CITATION_RE.finditer(cleaned):
        path, start, end = match.group(1), int(match.group(2)), match.group(3)
        end_line = int(end) if end is not None else start
        out.append(Citation(path=path, start_line=start, end_line=end_line, raw=match.group(0)))
    return out


def _file_line_count(workspace_root: Path, rel_path: str) -> int | None:
    """Return the file's line count, or None if it doesn't exist / isn't a file."""
    full = (workspace_root / rel_path).resolve()
    try:
        full.relative_to(workspace_root.resolve())
    except ValueError:
        return None
    if not full.is_file():
        return None
    try:
        with open(full, encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except OSError:
        return None


def verify_citation(
    citation: Citation,
    workspace_root: Path,
    touched_paths: set[str],
) -> CitationCheckResult:
    """Verify one citation is both real and grounded.

    ``touched_paths`` is the set of repository-relative paths that appeared
    in some tool response during the agent turn that produced ``citation``.
    A path is considered touched whether it was read in full (``read_file``)
    or returned by ``search_code`` / ``find_files`` / ``list_repo_structure``.
    """
    line_count = _file_line_count(workspace_root, citation.path)
    if line_count is None:
        return CitationCheckResult(
            citation=citation,
            real=False,
            grounded=citation.path in touched_paths,
            reason=f"path does not exist in workspace: {citation.path}",
        )

    if citation.start_line < 1 or citation.end_line > line_count:
        return CitationCheckResult(
            citation=citation,
            real=False,
            grounded=citation.path in touched_paths,
            reason=(
                f"{citation.path} has {line_count} lines but citation spans "
                f"{citation.start_line}-{citation.end_line}"
            ),
        )

    if citation.path not in touched_paths:
        return CitationCheckResult(
            citation=citation,
            real=True,
            grounded=False,
            reason=(
                f"{citation.path} was not read or searched during this turn; citation is ungrounded"
            ),
        )

    return CitationCheckResult(citation=citation, real=True, grounded=True, reason=None)


def verify_response(
    response_text: str,
    workspace_root: Path,
    touched_paths: set[str],
) -> list[CitationCheckResult]:
    """Run :func:`verify_citation` over every citation found in ``response_text``."""
    return [
        verify_citation(c, workspace_root, touched_paths) for c in extract_citations(response_text)
    ]
