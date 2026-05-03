"""Citation verifier + eval harness tests.

The rules of evidence in `agent/ada/agent.py` (citation discipline) are
load-bearing — without a regression gate, a model swap or prompt edit can
silently let hallucinated citations slip through. These tests exercise:

1. The pure-function citation library (extract + verify).
2. The bundled golden set (every entry's expectation matches reality).

Lives under `agent/tests/` so it runs in the same pytest invocation as the
rest of Ada's tests, AND is wrapped by the dedicated CI workflow
(`.github/workflows/ada-evals.yml`) for visibility on PRs touching agent/.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from evals.citations import (
    Citation,
    extract_citations,
    verify_citation,
    verify_response,
)
from evals.run_evals import DEFAULT_GOLDEN_SET, DEFAULT_WORKSPACE, run

if TYPE_CHECKING:
    from pathlib import Path


class TestExtractCitations:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("see agent/ada/agent.py:42", [("agent/ada/agent.py", 42, 42)]),
            ("range agent/auth.py:10-20", [("agent/auth.py", 10, 20)]),
            (
                "two: agent/auth.py:1 and agent/serve.py:5",
                [("agent/auth.py", 1, 1), ("agent/serve.py", 5, 5)],
            ),
            ("plain README.md:1", [("README.md", 1, 1)]),
            (".github/workflows/ci.yml:1", [(".github/workflows/ci.yml", 1, 1)]),
        ],
    )
    def test_basic_extraction(self, text: str, expected: list[tuple[str, int, int]]) -> None:
        cites = extract_citations(text)
        actual = [(c.path, c.start_line, c.end_line) for c in cites]
        assert actual == expected

    @pytest.mark.parametrize(
        "text",
        [
            "no citations here",
            "https://example.com:443/path is a URL",
            "the time is 12:34 right now",
            "https://gateway.ai-identity.co:443/gateway/enforce",
            "version 1.2.3 was released",  # period+digits but no `:N`
            "use ratio 16:9 for the layout",
        ],
    )
    def test_no_false_positives(self, text: str) -> None:
        assert extract_citations(text) == []

    def test_does_not_match_inside_url(self) -> None:
        # Even though "co:443" has shape close to ext:line, the URL prefix `//`
        # blocks the lookbehind so we don't mis-extract.
        text = "Ada POSTs to https://gateway.ai-identity.co:443 around 12:34"
        assert extract_citations(text) == []

    def test_extracts_from_mixed_url_and_path(self) -> None:
        # If the same text contains a real citation alongside a URL, we get
        # only the real citation.
        text = "POSTs to https://gateway.ai-identity.co:443 — see agent/ada/audit.py:1"
        cites = extract_citations(text)
        assert len(cites) == 1
        assert cites[0].path == "agent/ada/audit.py"
        assert cites[0].start_line == 1


class TestVerifyCitation:
    def test_real_and_grounded_passes(self, tmp_path: Path) -> None:
        (tmp_path / "foo.py").write_text("a\nb\nc\n")
        c = Citation("foo.py", 2, 2, "foo.py:2")
        result = verify_citation(c, tmp_path, {"foo.py"})
        assert result.passed is True
        assert result.real is True
        assert result.grounded is True

    def test_missing_path_fails_real(self, tmp_path: Path) -> None:
        c = Citation("missing.py", 1, 1, "missing.py:1")
        result = verify_citation(c, tmp_path, {"missing.py"})
        assert result.passed is False
        assert result.real is False
        assert "does not exist" in (result.reason or "")

    def test_out_of_range_fails_real(self, tmp_path: Path) -> None:
        (tmp_path / "short.py").write_text("a\nb\n")
        c = Citation("short.py", 99, 99, "short.py:99")
        result = verify_citation(c, tmp_path, {"short.py"})
        assert result.passed is False
        assert result.real is False
        assert "2 lines" in (result.reason or "")

    def test_line_zero_fails_real(self, tmp_path: Path) -> None:
        (tmp_path / "x.py").write_text("a\n")
        c = Citation("x.py", 0, 0, "x.py:0")
        result = verify_citation(c, tmp_path, {"x.py"})
        assert result.real is False

    def test_real_but_not_grounded(self, tmp_path: Path) -> None:
        (tmp_path / "real.py").write_text("a\nb\n")
        c = Citation("real.py", 1, 1, "real.py:1")
        result = verify_citation(c, tmp_path, set())  # nothing touched
        assert result.real is True
        assert result.grounded is False
        assert result.passed is False
        assert "ungrounded" in (result.reason or "")

    def test_range_within_file_passes(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("\n".join(str(i) for i in range(10)) + "\n")
        c = Citation("f.py", 2, 5, "f.py:2-5")
        assert verify_citation(c, tmp_path, {"f.py"}).passed is True

    def test_range_partially_out_of_file_fails(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("a\nb\nc\n")
        c = Citation("f.py", 2, 100, "f.py:2-100")
        assert verify_citation(c, tmp_path, {"f.py"}).real is False

    def test_path_traversal_fails_real(self, tmp_path: Path) -> None:
        # `..` paths must not resolve outside the workspace and report missing.
        c = Citation("../../../etc/passwd", 1, 1, "../../../etc/passwd:1")
        result = verify_citation(c, tmp_path, {"../../../etc/passwd"})
        assert result.real is False


class TestVerifyResponse:
    def test_no_citations_returns_empty(self, tmp_path: Path) -> None:
        results = verify_response("nothing to cite here", tmp_path, set())
        assert results == []

    def test_runs_per_citation(self, tmp_path: Path) -> None:
        (tmp_path / "good.py").write_text("a\n")
        results = verify_response(
            "good.py:1 and missing.py:1",
            tmp_path,
            {"good.py", "missing.py"},
        )
        assert len(results) == 2
        assert results[0].passed is True
        assert results[1].real is False


class TestGoldenSetMatchesExpectations:
    """Run the bundled golden set and assert every case matches its declared `expect`.

    This is the actual CI gate body — if a future code change breaks a
    case, it shows up here as a labeled diff (expect vs actual), not as
    a vague pytest red.
    """

    def test_all_cases_match(self) -> None:
        results = run(DEFAULT_GOLDEN_SET, DEFAULT_WORKSPACE)
        mismatches = [r for r in results if not r.matched]
        if mismatches:
            lines = [
                f"{r.case_id}: expect={r.expect} actual={r.actual} ({r.detail})" for r in mismatches
            ]
            pytest.fail(f"{len(mismatches)} golden-set case(s) failed:\n  " + "\n  ".join(lines))

    def test_golden_set_has_positive_and_negative_coverage(self) -> None:
        # Sanity: the gate is only useful if it includes both kinds of case.
        # If a future cleanup accidentally drops all the negatives, the gate
        # silently weakens — catch that here.
        from evals.run_evals import load_cases

        cases = load_cases(DEFAULT_GOLDEN_SET)
        assert any(c.expect == "pass" for c in cases), "no positive cases"
        assert any(c.expect.startswith("fail_") for c in cases), "no negative cases"
        assert len(cases) >= 10, f"golden set is too small: {len(cases)}"
