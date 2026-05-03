"""search_code path_glob handling, including the `**/` recursive case.

Regression test for the dogfood failure mode logged on 2026-05-03: Ada
called ``search_code('_is_secret_path', path_glob='**/test_*.py')``,
got 0 matches, and concluded "no tests exist" — even though
``agent/tests/test_code_tools_secrets.py`` had 6 references to that
function. Root cause: the grep fallback joined ``root / path_glob`` to
build a positional path argument, which grep treated literally because
``subprocess.run`` does not expand shell globs. The literal path
``/repo/**/test_*.py`` does not exist on disk → grep exits silently
with no matches.

Fixed by pre-enumerating files via ``pathlib.glob`` in the grep fallback
path (rg already handled this natively via ``-g``). These tests pin the
behavior so it cannot regress.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from ada.tools import code_tools
from ada.tools.code_tools import search_code

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


def _force_grep_fallback(monkeypatch: MonkeyPatch) -> None:
    """Make `_has_command('rg')` return False so we exercise the grep path
    even on machines that have ripgrep installed."""
    real = code_tools._has_command

    def fake(name: str) -> bool:
        if name == "rg":
            return False
        return real(name)

    monkeypatch.setattr(code_tools, "_has_command", fake)


class TestGrepFallbackHandlesRecursiveGlob:
    """Regression: `**/test_*.py` must find matches at any depth, not 0."""

    def test_recursive_glob_finds_nested_match(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        _force_grep_fallback(monkeypatch)

        nested = tmp_path / "pkg" / "tests"
        nested.mkdir(parents=True)
        (nested / "test_widget.py").write_text("def test_thing():\n    return 1\n")
        (tmp_path / "pkg" / "module.py").write_text("def helper(): pass\n")

        result = search_code("def test_thing", path_glob="**/test_*.py")
        assert result["status"] == "success"
        assert result["match_count"] == 1
        assert any("test_widget.py" in m for m in result["matches"])

    def test_recursive_glob_skips_non_matching(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        _force_grep_fallback(monkeypatch)

        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_a.py").write_text("MARKER\n")
        (tmp_path / "tests" / "helper.py").write_text("MARKER\n")  # not test_*

        result = search_code("MARKER", path_glob="**/test_*.py")
        assert result["status"] == "success"
        assert result["match_count"] == 1
        assert any("test_a.py" in m for m in result["matches"])
        assert all("helper.py" not in m for m in result["matches"])

    def test_recursive_glob_no_matches_returns_empty_not_error(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        # When the glob enumerates zero files, we must return a clean empty
        # success — NOT an error. Empty matches are a valid signal Ada relies on
        # for "absence" claims (rule of evidence #4: show the search you ran).
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        _force_grep_fallback(monkeypatch)

        (tmp_path / "main.py").write_text("hello\n")  # no test_*.py at any depth

        result = search_code("anything", path_glob="**/test_*.py")
        assert result["status"] == "success"
        assert result["match_count"] == 0
        assert result["matches"] == []


class TestGrepFallbackDirectoryGlob:
    """Sanity: directory paths (not `**`) keep working through the fallback."""

    def test_directory_path_runs(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        _force_grep_fallback(monkeypatch)

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("def thing():\n    pass\n")

        result = search_code("def thing", path_glob="src/*.py")
        assert result["status"] == "success"
        assert result["match_count"] == 1


class TestRipgrepStillNativeOnGlobs:
    """Sanity: when rg is available, it gets the path_glob via -g (unchanged)."""

    def test_rg_path_includes_g_flag(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        # Force rg available regardless of the host
        monkeypatch.setattr(code_tools, "_has_command", lambda name: name == "rg")

        captured: dict[str, list[str]] = {}

        def fake_run(cmd: list[str], **kwargs: object) -> object:  # noqa: ARG001
            captured["cmd"] = cmd

            class _R:
                stdout = ""
                returncode = 1  # rg returns 1 on no matches; that's fine

            return _R()

        with patch.object(code_tools.subprocess, "run", fake_run):
            search_code("anything", path_glob="**/test_*.py")

        assert captured["cmd"][0] == "rg"
        assert "-g" in captured["cmd"]
        gi = captured["cmd"].index("-g")
        assert captured["cmd"][gi + 1] == "**/test_*.py"
