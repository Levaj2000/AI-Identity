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

    Returns content with each line prefixed by its line number (e.g.
    `   42|    except Exception:`). The framing is structural — when Ada
    cites `path:line`, she should copy the number to the left of the `|`
    rather than counting or estimating. This is a deliberate guardrail
    against the citation-fabrication failure mode logged through prompts
    #2-#4 of the May 1 dogfood session, where conclusions were correct but
    line numbers drifted by 40-100 lines.

    Args:
        path: Repository-relative path (e.g. `api/app/routers/agents.py`).

    Returns:
        dict with `status` ("success" | "error"), `path`, and either
        `content` (line-numbered) + `line_count` or `error_message`. Files
        larger than ~1 MB are truncated with a note.
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
            raw = f.read(max_bytes)
        truncated = size > max_bytes
        rel_path = str(target.relative_to(_workspace_root()))

        lines = raw.splitlines()
        line_count = len(lines)
        # Width matches the largest line number so columns stay aligned —
        # easier for the model to read line numbers as a column.
        width = max(4, len(str(line_count)))
        header = f"=== {rel_path} ({line_count} lines) ==="
        if truncated:
            header += " [truncated at 1 MB]"
        numbered = "\n".join(f"{i:>{width}}|{line}" for i, line in enumerate(lines, start=1))
        content = f"{header}\n{numbered}\n"

        return {
            "status": "success",
            "path": rel_path,
            "content": content,
            "line_count": line_count,
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

    cmd_str = " ".join(cmd)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "command": cmd_str,
            "error_message": "search timed out (30s limit)",
        }

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    capped = lines[:200]
    rel_matches = [_strip_root_prefix(line, root) for line in capped]

    return {
        "status": "success",
        "pattern": pattern,
        "path_glob": path_glob,
        "command": cmd_str,
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


_GIT_SKIP_PARTS = {".git", "node_modules", ".venv", "dist", "build", "__pycache__", ".next"}


def find_files(glob: str) -> dict:
    """Find files matching a glob pattern within the workspace.

    Faster than `list_repo_structure` for existence checks.

    Args:
        glob: Glob pattern relative to workspace root, e.g. `"**/test_*.py"`
            or `"common/models/*.py"`.

    Returns:
        dict with `status`, `glob`, `match_count`, and `matches` (list of
        repo-relative paths). Capped at 200.
    """
    root = _workspace_root()
    matches: list[str] = []
    try:
        for p in root.glob(glob):
            if any(part in _GIT_SKIP_PARTS for part in p.parts):
                continue
            if p.is_file():
                matches.append(str(p.relative_to(root)))
    except (OSError, ValueError) as exc:
        return {"status": "error", "glob": glob, "error_message": str(exc)}
    matches.sort()
    return {
        "status": "success",
        "glob": glob,
        "match_count": len(matches),
        "truncated": len(matches) > 200,
        "matches": matches[:200],
    }


def git_log(path: str | None = None, max_count: int = 20) -> dict:
    """Show recent git commits, optionally scoped to a path.

    Use to learn when a file last changed and what the commit messages say.
    Often the "why" of unexpected code lives in the commit, not the code.

    Args:
        path: Optional repo-relative path to filter commits to.
        max_count: How many commits to return. Default 20, max 100.

    Returns:
        dict with `status`, `path`, and `commits` (list of
        `{sha, author, date, subject}`).
    """
    root = _workspace_root()
    max_count = min(max(1, max_count), 100)
    cmd = [
        "git",
        "-C",
        str(root),
        "log",
        f"--max-count={max_count}",
        "--pretty=format:%H%x09%an%x09%ad%x09%s",
        "--date=iso-strict",
    ]
    if path:
        try:
            target = _resolve_safely(path)
        except PermissionError as exc:
            return {"status": "error", "path": path, "error_message": str(exc)}
        cmd += ["--", str(target.relative_to(root))]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)
    except subprocess.TimeoutExpired:
        return {"status": "error", "path": path, "error_message": "git log timed out"}
    if result.returncode != 0:
        return {
            "status": "error",
            "path": path,
            "error_message": result.stderr.strip() or "git log failed",
        }

    commits = []
    for line in result.stdout.splitlines():
        parts = line.split("\t", 3)
        if len(parts) == 4:
            sha, author, date, subject = parts
            commits.append({"sha": sha[:12], "author": author, "date": date, "subject": subject})
    return {
        "status": "success",
        "path": path,
        "max_count": max_count,
        "commit_count": len(commits),
        "commits": commits,
    }


def git_blame(path: str, line: int) -> dict:
    """Show who last touched a specific line and in what commit.

    Use when reading code that doesn't make sense — the commit message often
    explains the constraint or workaround.

    Args:
        path: Repo-relative path to the file.
        line: 1-based line number to blame.

    Returns:
        dict with `status`, `path`, `line`, `text` (the line itself), and
        commit info `{sha, author, date, subject}`.
    """
    try:
        target = _resolve_safely(path)
    except PermissionError as exc:
        return {"status": "error", "path": path, "error_message": str(exc)}
    if not target.is_file():
        return {"status": "error", "path": path, "error_message": f"not a file: {path}"}
    if line < 1:
        return {"status": "error", "path": path, "error_message": "line must be >= 1"}

    root = _workspace_root()
    rel = str(target.relative_to(root))

    blame_cmd = [
        "git",
        "-C",
        str(root),
        "blame",
        "-w",
        "--porcelain",
        f"-L{line},{line}",
        rel,
    ]
    try:
        blame = subprocess.run(blame_cmd, capture_output=True, text=True, timeout=15, check=False)
    except subprocess.TimeoutExpired:
        return {"status": "error", "path": path, "error_message": "git blame timed out"}
    if blame.returncode != 0 or not blame.stdout:
        return {
            "status": "error",
            "path": path,
            "error_message": blame.stderr.strip() or "git blame failed",
        }

    sha = blame.stdout.split(None, 1)[0]
    text = ""
    for raw in blame.stdout.splitlines():
        if raw.startswith("\t"):
            text = raw[1:]
            break

    log_cmd = [
        "git",
        "-C",
        str(root),
        "log",
        "-1",
        "--pretty=format:%H%x09%an%x09%ad%x09%s",
        "--date=iso-strict",
        sha,
    ]
    try:
        log = subprocess.run(log_cmd, capture_output=True, text=True, timeout=10, check=False)
    except subprocess.TimeoutExpired:
        return {"status": "error", "path": path, "error_message": "git log timed out"}

    commit = {"sha": sha[:12]}
    if log.returncode == 0 and log.stdout:
        parts = log.stdout.split("\t", 3)
        if len(parts) == 4:
            commit = {
                "sha": parts[0][:12],
                "author": parts[1],
                "date": parts[2],
                "subject": parts[3],
            }

    return {
        "status": "success",
        "path": rel,
        "line": line,
        "text": text,
        "commit": commit,
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
