"""Citation extraction + verification for Ada's responses.

Two checks per cited ``path:line``:

1. **Real** — the path exists in the workspace and the line is within the
   file's line count. Catches hallucinated files and out-of-range line
   numbers (the most common citation-fabrication failure mode logged
   through the May 1 dogfood session).

2. **Grounded** — the path appeared in *some* tool response this turn.
   Catches the case where Ada cites a file she never read or searched.

Plus one response-level check (added for #357):

3. **Sibling-check on absence claims (Rule #2)** — when the response
   makes an absence claim ("no tests exist", "not implemented", etc.),
   require corroborating evidence: either a sibling test path was read
   (path containing ``/tests``, ``test_*.py``, etc.) or the response
   text mentions a ``find_files`` / ``list_repo_structure`` call. A
   single search returning 0 is not sufficient — tools have bugs and
   patterns get spelled differently than expected.

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


# ── Rule #2: absence-claim sibling check ─────────────────────────────────
# Added for Sprint 13 #357. The verifier flags any response that asserts
# something doesn't exist without showing a corroborating second signal
# (sibling-path read, find_files, or list_repo_structure).

# Substrings that indicate an absence claim. Lowercased, matched as plain
# substring in the response text. Conservative on purpose — false
# positives are worse than false negatives here, since every flagged case
# becomes a CI gate failure that has to be reasoned about.
_ABSENCE_PHRASES: tuple[str, ...] = (
    "no tests exist",
    "no test exists",
    "no tests for",
    "no test for",
    "no matching",
    "no implementation",
    "not implemented",
    "isn't implemented",
    "is not implemented",
    "doesn't exist",
    "does not exist",
    "nothing handles",
    "0 matches",
    "0 results",
    "no matches",
    "no results",
)

# A "test path" is anything in a tests/ directory or a test_*.py file.
# Reading any such path counts as the (a) sibling-read corroboration for
# Rule #2. Listing a tests/ directory likewise counts.
_TEST_PATH_RE = re.compile(r"(^|/)tests?($|/)|test_[A-Za-z0-9_]+\.py")

# Tool-name mentions in the response text that constitute the (b)/(c)
# corroboration: a structural search beyond a single search_code call.
_CORROBORATING_TOOL_RE = re.compile(
    r"\b(find_files|list_repo_structure)\b",
)


def has_absence_claim(text: str) -> bool:
    """True if ``text`` contains a phrase that asserts absence of something."""
    lower = text.lower()
    return any(phrase in lower for phrase in _ABSENCE_PHRASES)


def shows_corroborating_evidence(text: str, touched_paths: set[str]) -> bool:
    """True if there's a sibling-path read OR a structural-tool mention.

    Either signal satisfies Rule #2 — the founder review wants two
    independent signals before an absence claim, but the verifier doesn't
    need to enforce *which* second signal was used.
    """
    if any(_TEST_PATH_RE.search(p) for p in touched_paths):
        return True
    return bool(_CORROBORATING_TOOL_RE.search(text))


def check_sibling_for_absence(text: str, touched_paths: set[str]) -> str | None:
    """Return ``None`` if compliant, or a reason string if Rule #2 is violated.

    A response is violation-free if either (a) it makes no absence claim,
    or (b) it makes an absence claim AND shows corroborating evidence.
    """
    if not has_absence_claim(text):
        return None
    if shows_corroborating_evidence(text, touched_paths):
        return None
    return (
        "absence claim made without corroborating evidence: no test/sibling path "
        "in touched_paths and no find_files/list_repo_structure mention in "
        "response (Rule #2)"
    )
