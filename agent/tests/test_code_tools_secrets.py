"""Secret-file denylist for read-only code tools.

Surfaced by the CTO Ada production-readiness audit (Insight #74) — read_file
on `.env`, `*.pem`, `*credential*`, `*secret*`, and anything inside `.git/`
would otherwise let a prompt-injected request exfiltrate credentials via the
tool response. The denylist applies to read_file, list_repo_structure,
find_files, and search_code (matches in denylisted files are filtered before
return).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ada.tools.code_tools import (
    _is_secret_path,
    find_files,
    list_repo_structure,
    read_file,
    search_code,
)


class TestIsSecretPath:
    @pytest.mark.parametrize(
        "path",
        [
            "agent/ada/.env",
            ".env",
            ".env.local",
            ".env.production",
            "config/.env.test",
            "deploy/server.pem",
            "config.pem",
            "google_credentials.json",
            "credential_store.txt",
            "my-secret-key.json",
            "appsecret.toml",
            "application_default_credentials.json",
            ".git/HEAD",
            ".git/config",
            "subdir/.git/objects/abc",
        ],
    )
    def test_secret_paths_caught(self, path: str) -> None:
        assert _is_secret_path(Path(path)) is True

    @pytest.mark.parametrize(
        "path",
        [
            "agent/ada/agent.py",
            "README.md",
            "src/main.py",
            ".gitignore",
            ".gitattributes",
            "docs/architecture.md",
            "test.txt",
            "config.json",
            "creds.json",  # similar root word but not on denylist
        ],
    )
    def test_safe_paths_pass(self, path: str) -> None:
        assert _is_secret_path(Path(path)) is False

    def test_case_insensitive(self) -> None:
        assert _is_secret_path(Path("MY_CREDENTIAL.txt")) is True
        assert _is_secret_path(Path("API_SECRET.json")) is True
        assert _is_secret_path(Path("CERT.PEM")) is True


class TestReadFileBlocksSecrets:
    def test_env_file_denied(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        (tmp_path / ".env").write_text("API_KEY=actual_secret\n")
        result = read_file(".env")
        assert result["status"] == "error"
        assert "denylist" in result["error_message"].lower()
        assert "actual_secret" not in str(result)

    def test_pem_file_denied(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        (tmp_path / "server.pem").write_text("-----BEGIN PRIVATE KEY-----\n")
        result = read_file("server.pem")
        assert result["status"] == "error"
        assert "denylist" in result["error_message"].lower()

    def test_credentials_json_denied(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        (tmp_path / "application_default_credentials.json").write_text('{"client_id":"x"}')
        result = read_file("application_default_credentials.json")
        assert result["status"] == "error"
        assert "denylist" in result["error_message"].lower()

    def test_secret_file_denied(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        (tmp_path / "appsecret.toml").write_text("token=abc123\n")
        result = read_file("appsecret.toml")
        assert result["status"] == "error"

    def test_dotgit_file_denied(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        gitdir = tmp_path / ".git"
        gitdir.mkdir()
        (gitdir / "HEAD").write_text("ref: refs/heads/main\n")
        result = read_file(".git/HEAD")
        assert result["status"] == "error"

    def test_safe_file_still_reads(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        (tmp_path / "main.py").write_text("print('hi')\n")
        result = read_file("main.py")
        assert result["status"] == "success"
        assert "print" in result["content"]

    def test_gitignore_still_reads(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # .gitignore is NOT on the denylist — it's a config file, not secret.
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        (tmp_path / ".gitignore").write_text("*.pyc\n")
        result = read_file(".gitignore")
        assert result["status"] == "success"


class TestFindFilesFiltersSecrets:
    def test_env_glob_returns_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        (tmp_path / ".env").write_text("X=1")
        (tmp_path / ".env.local").write_text("X=1")
        result = find_files("**/.env*")
        assert result["status"] == "success"
        assert result["matches"] == []
        assert result["match_count"] == 0

    def test_pem_filtered(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        (tmp_path / "server.pem").write_text("")
        (tmp_path / "main.py").write_text("")
        result = find_files("**/*")
        assert result["status"] == "success"
        names = [Path(m).name for m in result["matches"]]
        assert "main.py" in names
        assert "server.pem" not in names

    def test_safe_files_still_returned(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        (tmp_path / "a.py").write_text("")
        (tmp_path / "b.py").write_text("")
        (tmp_path / ".env").write_text("X=1")
        result = find_files("**/*.py")
        assert result["status"] == "success"
        assert sorted(result["matches"]) == ["a.py", "b.py"]


class TestListRepoStructureFiltersSecrets:
    def test_pem_excluded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        (tmp_path / "main.py").write_text("")
        (tmp_path / "server.pem").write_text("")
        (tmp_path / "creds.json").write_text("")  # control: similar but not on denylist
        result = list_repo_structure(".")
        assert result["status"] == "success"
        tree = result["tree"]
        assert "main.py" in tree
        assert "server.pem" not in tree
        assert "creds.json" in tree

    def test_credential_file_excluded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        (tmp_path / "main.py").write_text("")
        (tmp_path / "google_credentials.json").write_text("{}")
        result = list_repo_structure(".")
        tree = result["tree"]
        assert "main.py" in tree
        assert "google_credentials.json" not in tree


class TestSearchCodeFiltersSecrets:
    def test_secret_match_filtered(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        (tmp_path / "appsecret.toml").write_text("API_TOKEN=actual_secret_value\n")
        (tmp_path / "main.py").write_text("API_TOKEN = os.getenv('API_TOKEN')\n")
        result = search_code("API_TOKEN")
        assert result["status"] == "success"
        joined = "\n".join(result["matches"])
        assert "main.py" in joined
        # Neither the secret filename nor its contents should leak through.
        assert "appsecret.toml" not in joined
        assert "actual_secret_value" not in joined

    def test_pem_match_filtered(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ADA_WORKSPACE_ROOT", str(tmp_path))
        (tmp_path / "server.pem").write_text("BEGIN PRIVATE KEY abc123\n")
        (tmp_path / "notes.md").write_text("BEGIN PRIVATE KEY referenced here\n")
        result = search_code("BEGIN PRIVATE KEY")
        assert result["status"] == "success"
        joined = "\n".join(result["matches"])
        assert "notes.md" in joined
        assert "server.pem" not in joined
