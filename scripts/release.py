#!/usr/bin/env python3
"""release.py — one-command release cut.

Replicates the repo's release precedent (0.3.0 / 0.4.0 cuts, 0.2.0 coordinated
version bump) as a single checked operation:

Checks (all run before anything is written):
  1. Git repo with CHANGELOG.md and pyproject.toml.
  2. No staged or modified tracked files (untracked files are listed, allowed).
  3. On the default branch, exactly at origin/<default> (fetches first).
  4. Version is strict X.Y.Z, greater than the latest CHANGELOG release, and
     tag vX.Y.Z exists neither locally nor on origin.
  5. The Unreleased section is non-empty.
  6. Backfill audit: every past CHANGELOG release header has a matching tag
     (--backfill creates the missing ones at the commit that added the header).
  7. Tests: bare `pytest` (pyproject testpaths — NOT `make test`), plus
     `npm test` in dashboard/ when that package defines one.

Writes:
  - CHANGELOG.md: "## [X.Y.Z]<sep><date>" inserted under "## [Unreleased]",
    reusing the previous release header's separator verbatim.
  - pyproject.toml: [project] version bump.
  - k8s/configmap.yaml, .env.example, common/config/settings.py: version-string
    lines bumped when present (the 0.2.0 coordinated-bump precedent).
  - One commit, one annotated tag vX.Y.Z.

Nothing is pushed without --push.

Usage:
  scripts/release.py 0.5.0                 cut the release (no push)
  scripts/release.py 0.5.0 --dry-run       show the plan, change nothing
  scripts/release.py 0.5.0 --push          also push the branch and new tags
  scripts/release.py 0.5.0 --backfill      also tag past releases missing tags
  scripts/release.py 0.5.0 --skip-tests    skip the suites (loud warning)
"""

import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HEADER_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\](.*?)(\d{4}-\d{2}-\d{2})\s*$")
VERSION_LINE_RE = re.compile(r'^(\s*[\w.]*version[\w.]*\s*[:=]\s*["\']?)', re.IGNORECASE)
EXTRA_VERSION_FILES = ["k8s/configmap.yaml", ".env.example", "common/config/settings.py"]


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def note(msg):
    print(f"  {msg}")


def sh(args, cwd, check=True):
    r = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if check and r.returncode != 0:
        fail(
            f"command failed: {' '.join(str(a) for a in args)}\n{r.stderr.strip() or r.stdout.strip()}"
        )
    return r


def semver_tuple(v):
    return tuple(int(p) for p in v.split("."))


def parse_args():
    p = argparse.ArgumentParser(
        description="Cut a release: changelog promotion + version bump + tag."
    )
    p.add_argument("version", help="X.Y.Z (no leading v)")
    p.add_argument(
        "--date", default=datetime.date.today().isoformat(), help="release date, default today"
    )
    p.add_argument("--dry-run", action="store_true", help="print the plan; write nothing")
    p.add_argument("--push", action="store_true", help="push the branch and the new tags to origin")
    p.add_argument(
        "--backfill", action="store_true", help="create tags for past releases that lack one"
    )
    p.add_argument(
        "--skip-tests", action="store_true", help="skip test suites (prints a loud warning)"
    )
    p.add_argument("--no-fetch", action="store_true", help="skip git fetch (offline)")
    return p.parse_args()


def main():
    args = parse_args()
    if not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        fail(f"version must be strict X.Y.Z, got: {args.version!r}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
        fail(f"--date must be YYYY-MM-DD, got: {args.date!r}")

    root = Path(sh(["git", "rev-parse", "--show-toplevel"], Path.cwd()).stdout.strip())
    changelog = root / "CHANGELOG.md"
    pyproject = root / "pyproject.toml"
    for f in (changelog, pyproject):
        if not f.exists():
            fail(f"{f.name} not found at repo root ({root})")

    print(f"Repo: {root}")
    print(f"Cutting v{args.version} ({args.date})" + ("  [DRY RUN]" if args.dry_run else ""))

    # 2. clean tracked tree
    dirty = sh(["git", "status", "--porcelain", "--untracked-files=no"], root).stdout.strip()
    if dirty:
        fail("tracked working tree is not clean:\n" + dirty)
    untracked = sh(["git", "status", "--porcelain"], root).stdout.strip()
    if untracked:
        note("untracked files present (allowed, untouched):")
        for line in untracked.splitlines():
            note("  " + line)

    # 3. default branch, synced with origin
    branch = sh(["git", "symbolic-ref", "--short", "HEAD"], root).stdout.strip()
    default_ref = sh(["git", "symbolic-ref", "-q", "refs/remotes/origin/HEAD"], root, check=False)
    default_branch = default_ref.stdout.strip().removeprefix("refs/remotes/origin/") or "main"
    if branch != default_branch:
        fail(f"cut from the default branch: on {branch!r}, expected {default_branch!r}")
    if not args.no_fetch:
        sh(["git", "fetch", "origin", default_branch], root)
    head = sh(["git", "rev-parse", "HEAD"], root).stdout.strip()
    remote = sh(["git", "rev-parse", f"origin/{default_branch}"], root).stdout.strip()
    if head != remote:
        fail(f"HEAD ({head[:8]}) != origin/{default_branch} ({remote[:8]}) — sync first")

    # 4. version ordering + tag availability
    text = changelog.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    releases = [
        (i, m.group(1), m.group(2), m.group(3))
        for i, line in enumerate(lines)
        if (m := HEADER_RE.match(line.rstrip("\n")))
    ]
    if not releases:
        fail("no dated release header found in CHANGELOG.md")
    latest_idx, latest_ver, sep, _ = releases[0]
    if semver_tuple(args.version) <= semver_tuple(latest_ver):
        fail(f"version {args.version} must be greater than latest changelog release {latest_ver}")
    tag = f"v{args.version}"
    if tag in sh(["git", "tag", "-l", tag], root).stdout.split():
        fail(f"tag {tag} already exists locally")
    remote_tags = sh(["git", "ls-remote", "--tags", "origin", tag], root).stdout.strip()
    if remote_tags:
        fail(f"tag {tag} already exists on origin")
    note(f"latest release: {latest_ver} → cutting {args.version}")

    # 5. Unreleased non-empty
    try:
        unrel_idx = next(i for i, line in enumerate(lines) if line.strip() == "## [Unreleased]")
    except StopIteration:
        fail("no '## [Unreleased]' header in CHANGELOG.md")
    section_end = next(
        (i for i in range(unrel_idx + 1, len(lines)) if lines[i].startswith("## [")), len(lines)
    )
    if not any(line.startswith(("- ", "### ")) for line in lines[unrel_idx + 1 : section_end]):
        fail("Unreleased section is empty — nothing to release")

    # 6. backfill audit
    existing_tags = set(sh(["git", "tag", "-l"], root).stdout.split())
    missing = [v for _, v, _, _ in releases if f"v{v}" not in existing_tags]
    backfill_plan = []
    if missing:
        if not args.backfill:
            note(
                "WARNING: past releases without tags: "
                + ", ".join(missing)
                + " (rerun with --backfill to create)"
            )
        for v in missing:
            if not args.backfill:
                continue
            pick = sh(
                ["git", "log", "--format=%H", "--reverse", "-S", f"## [{v}]", "--", "CHANGELOG.md"],
                root,
            ).stdout.split()
            if not pick:
                fail(f"cannot locate the commit that cut {v}; tag it manually")
            backfill_plan.append((v, pick[0]))
            note(f"backfill: v{v} -> {pick[0][:8]} (commit that added the header)")

    # 7. tests
    if args.skip_tests:
        note("WARNING: test suites skipped (--skip-tests)")
    else:
        if shutil.which("pytest"):
            print("Running pytest (full suite per pyproject testpaths)...")
            if subprocess.run(["pytest"], cwd=root).returncode != 0:
                fail("pytest failed — fix before cutting")
        else:
            fail("pytest not found on PATH (pip install pytest httpx cryptography)")
        dash_pkg = root / "dashboard" / "package.json"
        if dash_pkg.exists():
            scripts = json.loads(dash_pkg.read_text()).get("scripts", {})
            if "test" in scripts:
                if not (root / "dashboard" / "node_modules").exists():
                    fail("dashboard/node_modules missing — run: npm --prefix dashboard install")
                print("Running dashboard npm test...")
                if (
                    subprocess.run(["npm", "--prefix", "dashboard", "test"], cwd=root).returncode
                    != 0
                ):
                    fail("dashboard tests failed — fix before cutting")

    # planned edits
    new_header = f"## [{args.version}]{sep}{args.date}\n"
    insert_at = unrel_idx + 1
    while insert_at < len(lines) and lines[insert_at].strip() == "":
        insert_at += 1
    print("\nPlanned writes:")
    note(f"CHANGELOG.md: insert {new_header.strip()!r} before line {insert_at + 1}")
    note(f"pyproject.toml: [project] version -> {args.version}")

    versioned = []
    for rel in EXTRA_VERSION_FILES:
        f = root / rel
        if not f.exists():
            continue
        old_lines = f.read_text(encoding="utf-8").splitlines(keepends=True)
        new_lines, hits = [], 0
        for line in old_lines:
            m = VERSION_LINE_RE.match(line)
            if m and m.end() < len(line) and line[m.end() :].lstrip("\"'").startswith(latest_ver):
                line = line[: m.end()] + line[m.end() :].replace(latest_ver, args.version, 1)
                hits += 1
            new_lines.append(line)
        if hits:
            versioned.append((f, new_lines))
            note(f"{rel}: bump {hits} version line(s)")

    py_lines = pyproject.read_text(encoding="utf-8").splitlines(keepends=True)
    bumped = False
    in_project = False
    for i, line in enumerate(py_lines):
        stripped = line.strip()
        if stripped.startswith("["):
            in_project = stripped == "[project]"
        elif in_project and stripped.startswith("version") and "=" in stripped:
            py_lines[i] = re.sub(r'"(?:\d+\.\d+\.\d+)"', f'"{args.version}"', line, count=1)
            bumped = True
            break
    if not bumped:
        fail("could not find [project] version in pyproject.toml")

    if args.dry_run:
        print("\nDry run — no files changed, no commit, no tag.")
        return

    # writes
    lines.insert(insert_at, new_header + "\n")
    changelog.write_text("".join(lines), encoding="utf-8")
    pyproject.write_text("".join(py_lines), encoding="utf-8")
    for f, new_lines in versioned:
        f.write_text("".join(new_lines), encoding="utf-8")

    changed = ["CHANGELOG.md", "pyproject.toml"] + [str(f.relative_to(root)) for f, _ in versioned]
    sh(["git", "add", *changed], root)
    subject = f"chore(release): cut {args.version}"
    body = (
        f"Roll the Unreleased changelog section into the dated {args.version} release and bump "
        f"version files from {latest_ver} to {args.version}."
    )
    sh(["git", "commit", "-m", subject, "-m", body], root)
    sh(["git", "tag", "-a", tag, "-m", f"v{args.version}"], root)
    for v, commit in backfill_plan:
        sh(["git", "tag", "-a", f"v{v}", "-m", f"v{v} (backfilled)", commit], root)
        note(f"tagged v{v} at {commit[:8]}")

    print(f"\nCut complete: commit + annotated tag {tag} (local only).")
    if args.push:
        sh(
            ["git", "push", "origin", default_branch],
            root,
        )
        for t in [tag] + [f"v{v}" for v, _ in backfill_plan]:
            sh(["git", "push", "origin", t], root)
        print("Pushed branch and tags to origin.")
    else:
        print("To publish:")
        note(f"git push origin {default_branch}")
        note(f"git push origin {tag}" + "".join(f" v{v}" for v, _ in backfill_plan))
        note(f"gh release create {tag} --notes-from-tag")


if __name__ == "__main__":
    main()
