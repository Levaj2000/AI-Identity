"""Eval harness CLI for Ada — citation verification gate.

Static mode (default, used by CI):
    python -m evals.run_evals
or:
    python -m evals.run_evals --golden-set evals/golden_set.jsonl

Loads ``golden_set.jsonl`` (one entry per line) and runs the citation
verifier on each entry's pre-baked ``response`` + ``touched_paths``.
Each entry declares ``expect: pass | fail_real | fail_grounded`` so we
can include negative cases that *must* fail the verifier (intentional
drift) and treat them as test signal.

Live mode (planned, deferred):
    python -m evals.run_evals --live

Would invoke Ada via ADK runner per prompt and capture real tool calls.
Excluded from CI to keep PRs cheap and fast — that's a developer-run
sanity check, not a per-PR gate.

Exit code: 0 if all entries match their declared expectation; non-zero
otherwise. CI fails the PR on non-zero.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .citations import verify_response

DEFAULT_GOLDEN_SET = Path(__file__).parent / "golden_set.jsonl"
DEFAULT_WORKSPACE = Path(__file__).resolve().parents[2]  # repo root


@dataclass(frozen=True)
class EvalCase:
    """One entry from the golden set."""

    case_id: str
    prompt: str
    response: str
    touched_paths: set[str]
    expect: str  # "pass" | "fail_real" | "fail_grounded"


@dataclass(frozen=True)
class EvalResult:
    case_id: str
    expect: str
    actual: str  # "pass" | "fail_real" | "fail_grounded"
    matched: bool
    detail: str


def load_cases(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            stripped = raw.strip()
            if not stripped or stripped.startswith("//"):
                continue
            entry: dict[str, Any] = json.loads(stripped)
            cases.append(
                EvalCase(
                    case_id=entry["id"],
                    prompt=entry["prompt"],
                    response=entry["response"],
                    touched_paths=set(entry.get("touched_paths", [])),
                    expect=entry["expect"],
                )
            )
    return cases


def run_case(case: EvalCase, workspace: Path) -> EvalResult:
    results = verify_response(case.response, workspace, case.touched_paths)

    if not results:
        actual = "pass"
        detail = "no citations found"
    elif all(r.passed for r in results):
        actual = "pass"
        detail = f"{len(results)} citation(s) verified"
    else:
        any_real_failure = any(not r.real for r in results)
        actual = "fail_real" if any_real_failure else "fail_grounded"
        first_bad = next(r for r in results if not r.passed)
        detail = first_bad.reason or "citation failed verification"

    return EvalResult(
        case_id=case.case_id,
        expect=case.expect,
        actual=actual,
        matched=actual == case.expect,
        detail=detail,
    )


def run(golden_set: Path, workspace: Path) -> list[EvalResult]:
    return [run_case(case, workspace) for case in load_cases(golden_set)]


def _format_results(results: list[EvalResult]) -> str:
    lines: list[str] = []
    for r in results:
        marker = "✓" if r.matched else "✗"
        lines.append(f"  {marker} [{r.case_id}] expect={r.expect} actual={r.actual} — {r.detail}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ada citation eval harness")
    parser.add_argument("--golden-set", type=Path, default=DEFAULT_GOLDEN_SET)
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Reserved for live ADK runs (not implemented; CI must not pass --live).",
    )
    args = parser.parse_args(argv)

    if args.live:
        print("ERROR: --live mode is not yet implemented. Static mode is CI-safe.", file=sys.stderr)
        return 2

    if not args.golden_set.is_file():
        print(f"ERROR: golden set not found: {args.golden_set}", file=sys.stderr)
        return 2

    results = run(args.golden_set, args.workspace)
    print(f"Ada citation evals — {len(results)} case(s)")
    print(_format_results(results))

    fails = [r for r in results if not r.matched]
    if fails:
        print(f"\n{len(fails)} case(s) did not match expectation. CI gate FAIL.", file=sys.stderr)
        return 1

    print(f"\nAll {len(results)} cases matched expectation. CI gate PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
