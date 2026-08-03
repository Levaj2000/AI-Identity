#!/usr/bin/env python3
"""Verify each service's requirements.lock is consistent with its requirements.txt.

Deliberately NOT a regenerate-and-diff check: `uv pip compile` resolves unpinned
transitive deps to the newest satisfying release, so a byte-diff guard would start
failing whenever PyPI moves, with no repo change. The failure mode that actually
bites is bumping a pin in requirements.txt and forgetting the lock — so we check
that every direct requirement appears in the lock at the exact pinned version.

Regeneration command lives in each lock file's header.
"""

import pathlib
import re
import sys

SERVICES = ["api", "gateway", "mandate"]


def norm(name: str) -> str:
    """PEP 503 name normalization."""
    return re.sub(r"[-_.]+", "-", name).lower()


def direct_pins(path: pathlib.Path) -> dict[str, str | None]:
    """name -> exact version for `==` pins, None for range specs."""
    pins: dict[str, str | None] = {}
    for raw in path.read_text().splitlines():
        line = raw.split("#")[0].strip()
        if not line:
            continue
        m = re.match(r"^([A-Za-z0-9._-]+)(\[[^\]]*\])?\s*([<>=!~].*)$", line)
        if not m:
            continue
        spec = m.group(3).replace(" ", "")
        exact = re.match(r"^==([A-Za-z0-9.\-]+)$", spec)
        pins[norm(m.group(1))] = exact.group(1) if exact else None
    return pins


def locked_versions(path: pathlib.Path) -> dict[str, str]:
    versions: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        m = re.match(r"^([A-Za-z0-9._-]+)==([A-Za-z0-9.\-]+)", raw)
        if m:
            versions[norm(m.group(1))] = m.group(2)
    return versions


def main() -> int:
    fail = False
    for svc in SERVICES:
        req = pathlib.Path(svc, "requirements.txt")
        lock = pathlib.Path(svc, "requirements.lock")
        if not lock.exists():
            print(f"{svc}: {lock} is missing — generate it (see another lock's header)")
            fail = True
            continue
        locked = locked_versions(lock)
        for name, ver in direct_pins(req).items():
            if name not in locked:
                print(f"{svc}: {name} is in requirements.txt but absent from the lock — regenerate")
                fail = True
            elif ver is not None and locked[name] != ver:
                print(
                    f"{svc}: {name}=={ver} in requirements.txt but "
                    f"{name}=={locked[name]} in the lock — regenerate"
                )
                fail = True
    if not fail:
        print(f"lockfiles consistent for: {', '.join(SERVICES)}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
