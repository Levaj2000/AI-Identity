#!/usr/bin/env python3
"""Mirror the public Evidence Anchor checkpoint feed — with a rewrite alarm.

Run by ``.github/workflows/evidence-anchor-mirror.yml`` on a schedule. Pages
through ``GET /evidence-anchor/checkpoints`` (oldest first) and writes the
full history to ``<out>/checkpoints.ndjson`` (one signed DSSE checkpoint
entry per line, feed order) plus a small ``<out>/mirror-state.json``.

Before overwriting, it enforces the property that makes the mirror a witness
and not just a cache — **the history it already holds may only grow**:

* every previously mirrored ``merkle_root`` must still be present in the
  fresh fetch, with a byte-identical entry (envelope included), and
* no fresh entry may reuse a mirrored ``(org_id, first_audit_id)`` slot with
  a different root (that would be a rewritten batch).

Any violation prints a loud SPLIT-VIEW / ROLLBACK alert, refuses to update
the snapshot, and exits 2 — which fails the workflow run and triggers
GitHub's failure notification. The prior snapshot (and the git history of
the mirror branch) is the evidence.

Stdlib only, on purpose: the workflow runs it with a bare python3, and a
third party auditing the mirror can read everything it does in one file.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PAGE_SIZE = 500
SNAPSHOT = "checkpoints.ndjson"
STATE = "mirror-state.json"


def _canonical(entry: dict) -> str:
    return json.dumps(entry, sort_keys=True, separators=(",", ":"))


def fetch_history(base_url: str) -> list[dict]:
    """Page through the feed, oldest first, until every checkpoint is held."""
    entries: list[dict] = []
    offset = 0
    while True:
        query = urllib.parse.urlencode({"limit": PAGE_SIZE, "offset": offset})
        url = f"{base_url.rstrip('/')}/evidence-anchor/checkpoints?{query}"
        with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 — https feed URL
            page = json.load(resp)
        entries.extend(page["checkpoints"])
        offset += len(page["checkpoints"])
        if offset >= page["total"] or not page["checkpoints"]:
            return entries


def check_append_only(previous: list[dict], fresh: list[dict]) -> list[str]:
    """The mirrored history may only grow. Returns human-readable violations."""
    fresh_by_root = {e["merkle_root"]: e for e in fresh}
    fresh_by_slot = {(e["org_id"], e["first_audit_id"]): e for e in fresh}
    violations = []
    for held in previous:
        root = held["merkle_root"]
        slot = (held["org_id"], held["first_audit_id"])
        current = fresh_by_root.get(root)
        if current is None:
            gone_to = fresh_by_slot.get(slot)
            if gone_to is not None:
                violations.append(
                    f"REWRITTEN: org {slot[0]} batch starting at audit id {slot[1]} "
                    f"was root {root}, feed now serves root {gone_to['merkle_root']}"
                )
            else:
                violations.append(f"DISAPPEARED: mirrored checkpoint {root} is no longer served")
        elif _canonical(current) != _canonical(held):
            violations.append(f"MUTATED: checkpoint {root} is served with different content")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://api.ai-identity.co")
    parser.add_argument("--out", required=True, help="Mirror directory (the branch worktree).")
    args = parser.parse_args()

    out = Path(args.out)
    snapshot_path = out / SNAPSHOT
    previous: list[dict] = []
    if snapshot_path.exists():
        previous = [json.loads(line) for line in snapshot_path.read_text().splitlines() if line]

    fresh = fetch_history(args.base_url)
    print(f"fetched {len(fresh)} checkpoints from {args.base_url} (held: {len(previous)})")

    violations = check_append_only(previous, fresh)
    if violations:
        print("\n!!! EVIDENCE ANCHOR SPLIT-VIEW / ROLLBACK ALERT !!!", file=sys.stderr)
        print(
            "The public feed no longer extends the history this mirror holds.\n"
            "Refusing to update the snapshot — the current mirror branch is the "
            "evidence. Escalate to security@ai-identity.co.\n",
            file=sys.stderr,
        )
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 2

    out.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text("".join(_canonical(e) + "\n" for e in fresh))
    (out / STATE).write_text(
        json.dumps(
            {
                "source": args.base_url,
                "mirrored_at": datetime.datetime.now(tz=datetime.UTC).isoformat(),
                "checkpoints_held": len(fresh),
                "new_since_last_run": len(fresh) - len(previous),
            },
            indent=2,
        )
        + "\n"
    )
    print(f"snapshot written: {len(fresh)} checkpoints ({len(fresh) - len(previous)} new)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
