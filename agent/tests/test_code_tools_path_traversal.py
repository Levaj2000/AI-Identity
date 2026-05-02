"""Path-traversal protection for glob-taking tools in code_tools.

Surfaced by Ada's prompt #5 audit on 2026-05-01: search_code's grep
fallback joined `path_glob` to the workspace root via pathlib's `/`,
letting `path_glob="../../etc"` produce a grep target outside the
workspace. find_files passed `glob` straight to `pathlib.glob`, which
could yield out-of-root paths and leak them via the `relative_to`
ValueError message.
"""

from __future__ import annotations

import pytest
from ada.tools.code_tools import _validate_glob, find_files, search_code


class TestValidateGlob:
    @pytest.mark.parametrize(
        "pattern",
        ["**/*.py", "common/models/*.py", "agent/ada/tools/code_tools.py", "*"],
    )
    def test_safe_globs_pass(self, pattern: str) -> None:
        assert _validate_glob(pattern) is None

    @pytest.mark.parametrize(
        "pattern",
        [
            "../../etc",
            "../../etc/passwd",
            "agent/../../../etc",
            "foo/../../bar",
            "..",
            "../",
        ],
    )
    def test_dotdot_segments_rejected(self, pattern: str) -> None:
        err = _validate_glob(pattern)
        assert err is not None
        assert ".." in err

    @pytest.mark.parametrize("pattern", ["/etc", "/etc/passwd", "/"])
    def test_absolute_paths_rejected(self, pattern: str) -> None:
        err = _validate_glob(pattern)
        assert err is not None
        assert "absolute" in err

    def test_backslash_dotdot_rejected(self) -> None:
        # Windows-style separators normalized so `..` segments still caught.
        assert _validate_glob("..\\..\\etc") is not None


class TestSearchCodeRejectsTraversal:
    def test_grep_fallback_blocked(self) -> None:
        result = search_code("password", path_glob="../../etc")
        assert result["status"] == "error"
        assert "error_message" in result

    def test_safe_path_glob_runs(self) -> None:
        # Sanity: a legitimate scoped search reaches the search subprocess
        # rather than getting blocked by the validator. We use a directory
        # path (not a `**` glob) so this passes whether the test runs
        # against ripgrep or the grep fallback.
        result = search_code("def read_file", path_glob="agent/ada/tools")
        assert result["status"] == "success"


class TestFindFilesRejectsTraversal:
    def test_dotdot_glob_blocked(self) -> None:
        result = find_files("../../*")
        assert result["status"] == "error"
        assert ".." in result["error_message"]

    def test_absolute_glob_blocked(self) -> None:
        result = find_files("/etc/*")
        assert result["status"] == "error"
        assert "absolute" in result["error_message"]

    def test_safe_glob_runs(self) -> None:
        result = find_files("agent/ada/tools/*.py")
        assert result["status"] == "success"
        assert any("code_tools.py" in m for m in result["matches"])
