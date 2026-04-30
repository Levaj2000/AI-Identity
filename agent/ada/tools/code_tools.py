"""Read-only code-exploration tools for Ada.

The workspace root defaults to the AI Identity repository root (the directory
containing `pyproject.toml`). Override with the `ADA_WORKSPACE_ROOT` env var
when deploying Ada elsewhere.
"""

import os
import subprocess
from pathlib import Path


def _workspace_root() -> Path:
    """Resolve the workspace root.

    Priority:
    1. `ADA_WORKSPACE_ROOT` env var if set.
    2. Walk upward from this file looking for `pyproject.toml`.
    3. Fall back to CWD.
    """
    env = os.getenv("ADA_WORKSPACE_ROOT")
    if env:
        return Path(env).resolve()

    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


def _resolve_safely(path: str) -> Path:
    """Resolve `path` against the workspace root and reject traversal."""
    root = _workspace_root()
    target = (root / path).resolve()
    # Refuse paths that escape the workspace root
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise PermissionError(f"path '{path}' is outside workspace root {root}") from exc
    return target


def read_file(path: str) -> dict:
    """Read a file from the AI Identity repository.

    Args:
        path: Repository-relative path (e.g. `api/app/routers/agents.py`).

    Returns:
        dict with `status` ("success" | "error"), `path`, and either `content`
        or `error_message`. Files larger than ~1 MB are truncated with a note.
    """
    try:
        target = _resolve_safely(path)
    except PermissionError as exc:
        return {"status": "error", "path": path, "error_message": str(exc)}

    if not target.exists():
        return {"status": "error", "path": path, "error_message": f"file not found: {path}"}
    if not target.is_file():
        return {"status": "error", "path": path, "error_message": f"not a file: {path}"}

    try:
        size = target.stat().st_size
        max_bytes = 1_000_000
        with open(target, encoding="utf-8", errors="replace") as f:
            content = f.read(max_bytes)
        truncated = size > max_bytes
        return {
            "status": "success",
            "path": str(target.relative_to(_workspace_root())),
            "content": content,
            "size_bytes": size,
            "truncated": truncated,
        }
    except OSError as exc:
        return {"status": "error", "path": path, "error_message": str(exc)}


def search_code(pattern: str, path_glob: str | None = None) -> dict:
    """Search the codebase for a pattern.

    Uses ripgrep if available (fast); falls back to grep otherwise. Excludes
    common noise directories (.git, node_modules, .venv, dist, build).

    Args:
        pattern: Regex pattern to search for.
        path_glob: Optional glob to scope the search (e.g. `"api/**/*.py"`).

    Returns:
        dict with `status`, `match_count`, and `matches` (list of "path:line:text").
        Capped at 200 matches.
    """
    root = _workspace_root()
    cmd: list[str]

    if _has_command("rg"):
        cmd = [
            "rg",
            "--no-heading",
            "--with-filename",
            "--line-number",
            "--max-count",
            "10",
            pattern,
        ]
        if path_glob:
            cmd += ["-g", path_glob]
        cmd.append(str(root))
    else:
        cmd = [
            "grep",
            "-rn",
            "--exclude-dir=.git",
            "--exclude-dir=node_modules",
            "--exclude-dir=.venv",
            "--exclude-dir=dist",
            "--exclude-dir=build",
            "--exclude-dir=__pycache__",
            pattern,
            str(root if not path_glob else root / path_glob),
        ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "error_message": "search timed out (15s limit)"}

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    capped = lines[:200]
    rel_matches = [_strip_root_prefix(line, root) for line in capped]

    return {
        "status": "success",
        "pattern": pattern,
        "path_glob": path_glob,
        "match_count": len(lines),
        "truncated": len(lines) > 200,
        "matches": rel_matches,
    }


def list_repo_structure(path: str = ".", max_depth: int = 3) -> dict:
    """List the directory structure under `path`.

    Args:
        path: Repository-relative path (defaults to repo root).
        max_depth: How deep to recurse. Default 3.

    Returns:
        dict with `status`, `path`, and `tree` (list of relative entry strings).
    """
    try:
        target = _resolve_safely(path)
    except PermissionError as exc:
        return {"status": "error", "path": path, "error_message": str(exc)}

    if not target.exists():
        return {"status": "error", "path": path, "error_message": f"not found: {path}"}
    if not target.is_dir():
        return {"status": "error", "path": path, "error_message": f"not a directory: {path}"}

    skip_names = {".git", "node_modules", ".venv", "dist", "build", "__pycache__", ".next"}
    root = _workspace_root()
    entries: list[str] = []

    def _walk(current: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            children = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name))
        except OSError:
            return
        for child in children:
            if child.name in skip_names or child.name.startswith("."):
                continue
            rel = child.relative_to(root)
            suffix = "/" if child.is_dir() else ""
            entries.append(f"{rel}{suffix}")
            if child.is_dir():
                _walk(child, depth + 1)

    _walk(target, 1)
    return {
        "status": "success",
        "path": str(target.relative_to(root)) or ".",
        "max_depth": max_depth,
        "entry_count": len(entries),
        "tree": entries[:500],
        "truncated": len(entries) > 500,
    }


def _has_command(name: str) -> bool:
    """Return True if `name` is on PATH."""
    return (
        subprocess.run(
            ["which", name],
            capture_output=True,
            text=True,
            check=False,
        ).returncode
        == 0
    )


def _strip_root_prefix(line: str, root: Path) -> str:
    """Convert absolute paths in grep/rg output to repo-relative."""
    prefix = f"{root}/"
    if line.startswith(prefix):
        return line[len(prefix) :]
    return line
