#!/usr/bin/env python3
"""Reply to CodeRabbit review threads on praxis-proxy/policy #171 and #173.

Usage:
    python3 reply.py 171          dry run: print which thread gets which reply
    APPLY=1 python3 reply.py 171  post the replies and resolve the marked threads

Uses the gh CLI for every GitHub call. Skips threads that are already
resolved or that already carry a comment from the PR author.
"""

import json
import os
import subprocess
import sys

OWNER, REPO = "praxis-proxy", "policy"
ME = "Levaj2000"

ALLOW = (
    "Keeping #![allow] here. The block is the one the tree's own examples carry, and "
    "#![expect] fails the build whenever a listed lint does not fire, which is the case for "
    "several of these lints in at least one of the five examples. If the maintainers want "
    "expect across examples, that is a tree-wide change and I am happy to follow it in a "
    "separate PR."
)

# (name, resolve_after_reply, reply_text, matcher)
# A matcher gets (path, body_lowercase) and returns True for the thread it owns.
RULES_171 = [
    (
        "dsse with chain off: fixed",
        True,
        "Confirmed and fixed in the follow-up commit: the chain wrapper returned before the "
        "signer ran, so this pair emitted unsigned records under a signing policy. Construction "
        "now refuses it with a config error, with a test.",
        lambda p, b: (
            p.endswith("src/emitter.rs")
            and "dsse" in b
            and "chain" in b
            and "epoch" not in b
            and "restart" not in b
        ),
    ),
    (
        "uid collision across restarts and replicas: confirmed, upstream",
        False,
        "Confirmed, and it is a real finding, thank you; the replica case too. metadata.uid is "
        "chain_uid plus a counter, the counter restarts at 0 with the process, and the default "
        "chain_uid is derived from the plugin name rather than minted per process as the config "
        "comment claims. The stream stamps inside the hashed bytes keep the records distinct, but "
        "AID-EMIT-1 section 6 tells consumers to dedupe on metadata.uid, so a consumer holding "
        "the previous epoch would drop the new epoch's first records as replays. The fix adds a "
        "per-process component (startup time plus a nonce, so replicas differ too) and changes "
        "the uid format, which changes the hashed bytes and every committed conformance vector, "
        "so it lands in the AI-Identity crate first with a spec patch bump and regenerated "
        "vectors, and this port follows in its next push. Tracking it there; I will link the PR "
        "here.",
        lambda p, b: (
            p.endswith("src/emitter.rs")
            and ("epoch" in b or "restart" in b or "collision" in b or "replica" in b)
        ),
    ),
    (
        "inline allow to expect: declined",
        True,
        "Keeping #[allow] at these three sites, to match the tree rather than the path "
        "instruction: on main today there are 215 allow sites (143 #[allow], 72 #![allow]) "
        'against 18 expect, and the workspace lint set carries allow_attributes = "allow" '
        "with a comment saying why expect is not enforced. #[expect] also turns into an "
        "unfulfilled_lint_expectations warning wherever a listed lint does not fire, which "
        "under -D warnings is a build break. If the maintainers want to move the tree to "
        "expect, I will follow it for this crate in that change.",
        lambda p, b: p.endswith("src/emitter.rs") and "expect" in b,
    ),
    (
        "read_subject in panic_drive: fixed",
        True,
        "Fixed in the follow-up commit. The README already said to declare all four; the "
        "example's YAML had three.",
        lambda p, b: "read_subject" in b,
    ),
    (
        "SAMPLE-OUTPUT wording: fixed",
        True,
        "Reworded in the follow-up commit: the canonical form sorts keys itself "
        "(sign::canonical_bytes) and that is the only ordering a verifier depends on; the "
        "printed records match it because serde_json::Map is a BTreeMap without "
        "preserve_order, which the hashed bytes do not rely on.",
        lambda p, b: p.endswith("SAMPLE-OUTPUT.md"),
    ),
    (
        "examples allow to expect: declined",
        True,
        "Keeping #![allow] here, to match the tree rather than the path instruction: the block "
        "is the one the tree's own examples and integration tests carry (72 crate-level allow "
        "blocks on main, 5 expect), and #![expect] fails the build wherever a listed lint does "
        "not fire, which is the case for several of these lints in at least one of the five "
        "examples. If the maintainers want expect across examples, that is a tree-wide change "
        "and I am happy to follow it in a separate PR.",
        lambda p, b: "/examples/" in p and "expect" in b,
    ),
    (
        "deny_unknown_fields: fixed",
        True,
        "Agreed and fixed in the follow-up commit: #[serde(deny_unknown_fields)] on the config, "
        "with a test that a misspelled authority_uid fails construction. The tagged-enum shape "
        "for the signing fields is a good idea and a config-shape change; leaving it for the "
        "move to builtins.",
        lambda p, b: p.endswith("src/config.rs") and "deny_unknown_fields" in b,
    ),
    (
        "Praxis default identity: fixed",
        True,
        "Agreed and changed in the follow-up commit: the in-tree defaults now name Praxis. "
        "Every example and all three committed vectors set product_name and vendor_name "
        "explicitly, so no vector changes.",
        lambda p, b: p.endswith("src/config.rs") and ("vendor" in b or "product" in b),
    ),
    (
        "canonical key write without clone: fixed",
        True,
        "Taken in the follow-up commit: the key is written through serde_json::to_writer, same "
        "RFC 8785 escaping, no clone; the committed vectors are byte-identical.",
        lambda p, b: p.endswith("src/sign.rs") and "clon" in b,
    ),
    (
        "RFC 8785: confirmed, upstream (decline withdrawn)",
        False,
        "You are right, and I withdraw my earlier reply on this. cmf.mcp is serialized whole "
        "(annotations and schemas are open serde_json::Value) and violation details are copied "
        "as is, so floats and non-ASCII keys can reach the canonicalizer. The guards are "
        "debug_assert, so release builds do not panic, but a release build then emits bytes "
        "that are not RFC 8785 for such a record while still declaring serialization_id 2. The "
        "fix is a real RFC 8785 canonicalizer with tests for a float in a schema and a "
        "non-ASCII annotation key; because the record contract (AID-EMIT-1 section 4) and its "
        "stdlib validator currently constrain the value space, the widening lands in the spec, "
        "the crate and the validator together, with the uid fix, and this port follows in its "
        "next push. Tracking it there; I will link the PR here.",
        lambda p, b: p.endswith("src/sign.rs") and ("8785" in b or "canonical" in b),
    ),
    (
        "dependency pinning: done",
        True,
        "Done in the follow-up commit: p256 is pinned to the locked 0.14.0 in "
        "[workspace.dependencies], base64 is declared there once at the locked 0.23.1, and the "
        "plugin takes it with workspace = true. The lock is unchanged. The builtins that still "
        "declare base64 locally are left as they are, since that touches their crates; happy "
        "to include that swap if a maintainer wants it in this PR.",
        lambda p, b: p.endswith("Cargo.toml"),
    ),
]

RULES_173 = [
    (
        "AE10 exercises R22 with the opt-in on: fixed",
        True,
        "Agreed on all three points; fixed in the follow-up commit. AE10 now sets the raw-argument "
        "opt-in on both sinks, so the absence of the secret is R22's removal and not R5's digest "
        "default; it covers R5 and R22; the success criteria require AE1 through AE10; and R22 "
        "states that the opt-in renders what survived removal and cannot restore it.",
        lambda p, b: "ae10" in b or "opt-in" in b or "r22" in b,
    ),
    (
        "F5 tail completeness: fixed",
        True,
        "Agreed, and a good catch: a dense sequence from 0 cannot show a loss after the last "
        "exported record. The follow-up commit rewords F5 to say it shows no leading or interior "
        "gap, that a trailing loss leaves no gap to see, and that completeness at the tail needs "
        "a trusted terminal sequence or checkpoint from the host, which this document does not "
        "define.",
        lambda p, b: (
            "trailing" in b
            or "final stamped" in b
            or "last exported" in b
            or "false completeness" in b
            or "terminal" in b
        ),
    ),
    (
        "F5 gaps as evidence: fixed",
        True,
        "Agreed; F5 contradicted R8 as written. It now says a dense sequence opening at 0 means "
        "nothing was lost, and a gap or a non-zero head is reported as evidence of loss, not as "
        "a verification failure; the records on either side still verify on their own. That is "
        "also how the contract's own verification procedure words it.",
        lambda p, b: "stream_seq" in b or "dense" in b or "gap" in b,
    ),
    (
        "R5 keyed digests: fixed",
        True,
        "Agreed. R5 now requires the keyed digest where the host provides a key "
        "(engine_settings.content_provenance_key from #84, rendered as "
        "hmac-sha256:<key_id>:<hex>), keeps the key out of the record, and names the unkeyed "
        "sha256 form as guessable for low-entropy values rather than presenting it as "
        "redaction.",
        lambda p, b: "digest" in b or "cwe-200" in b or "redact" in b,
    ),
]

RULES = {171: RULES_171, 173: RULES_173}

QUERY = """
query($owner: String!, $repo: String!, $num: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $num) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          comments(first: 30) {
            nodes { databaseId path body author { login } }
          }
        }
      }
    }
  }
}
"""


def gh(*args, stdin=None):
    r = subprocess.run(["gh", *args], input=stdin, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        raise SystemExit(f"gh failed: {' '.join(args[:3])}")
    return r.stdout


def main():
    num = int(sys.argv[1])
    apply = os.environ.get("APPLY") == "1"
    rules = RULES[num]
    data = json.loads(
        gh(
            "api",
            "graphql",
            "-f",
            f"query={QUERY}",
            "-f",
            f"owner={OWNER}",
            "-f",
            f"repo={REPO}",
            "-F",
            f"num={num}",
        )
    )
    threads = data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    planned = 0
    for t in threads:
        comments = t["comments"]["nodes"]
        if not comments:
            continue
        first = comments[0]
        author = (first["author"] or {}).get("login", "")
        path = first["path"] or ""
        body = first["body"].lower()
        snippet = first["body"].strip().splitlines()[0][:70] if first["body"].strip() else ""
        if "coderabbit" not in author.lower():
            continue
        if t["isResolved"]:
            print(f"skip (resolved)      {path}: {snippet}")
            continue
        last_author = (comments[-1]["author"] or {}).get("login", "")
        answered = any(((c["author"] or {}).get("login") == ME) for c in comments)
        if answered and not (
            os.environ.get("FORCE") == "1" and "coderabbit" in last_author.lower()
        ):
            print(f"skip (you answered)  {path}: {snippet}")
            continue
        match = next(((n, res, txt) for n, res, txt, m in rules if m(path, body)), None)
        if match is None:
            print(f"NO RULE              {path}: {snippet}")
            continue
        name, resolve, text = match
        planned += 1
        action = "reply+resolve" if resolve else "reply"
        print(f"{action:<20} {path}: {snippet}\n{'':21}-> {name}")
        if not apply:
            continue
        gh(
            "api",
            "-X",
            "POST",
            f"repos/{OWNER}/{REPO}/pulls/{num}/comments/{first['databaseId']}/replies",
            "-f",
            f"body={text}",
        )
        if resolve:
            gh(
                "api",
                "graphql",
                "-f",
                "query=mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) "
                "{ thread { isResolved } } }",
                "-f",
                f"id={t['id']}",
            )
    print(f"\n{planned} thread(s) {'posted' if apply else 'would be posted'} on #{num}.")
    if not apply and planned:
        print(f"Re-run with APPLY=1 to post:  APPLY=1 python3 {sys.argv[0]} {num}")


if __name__ == "__main__":
    main()
