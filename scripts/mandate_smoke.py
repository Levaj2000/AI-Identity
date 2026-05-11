#!/usr/bin/env python3
"""Smoke test for the Mandate Service — designed to run inside the pod.

Exercises behaviour that the k8s liveness probe cannot:
  1. /health responds 200
  2. /api/v1/mandates/verify rejects a mandate with a garbage ECDSA signature
     (error must mention invalid signatures)
  3. /api/v1/mandates/verify rejects a mandate whose only signature is the
     ml-dsa-87 placeholder slot — regression guard for the unknown-algorithm
     spoofing path closed in the Ship-A hardening pass (mandate/app/routers/
     verify.py and mandate/app/signing.py, PR #259).

This script must run *inside* the mandate pod, talking to localhost:8003.
That's because the cluster blocks reaching the service from anywhere else:

  - The `ai-identity` namespace enforces PodSecurity `restricted:latest`,
    so a bare `kubectl run --image=curlimages/curl` is rejected
    (allowPrivilegeEscalation, capabilities.drop, runAsNonRoot).
  - The `allow-internal-to-mandate` NetworkPolicy only permits api/gateway
    pods to reach `mandate-service:8003`; an ad-hoc smoke pod has no
    matching labels and gets nothing.

Exec'ing into the existing mandate pod sidesteps both: loopback traffic
has no NetworkPolicy involvement, and the pod already passes PodSecurity.
The mandate container ships Python 3 (it's a FastAPI service), so no extra
image is needed.

Driven by scripts/mandate-smoke.sh, which does the `kubectl exec`.
Exit codes: 0 on full pass, non-zero on the first failure.
"""

from __future__ import annotations

import copy
import json
import sys
import urllib.error
import urllib.request

URL = "http://localhost:8003"
TIMEOUT = 15

GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


def ok(msg: str) -> None:
    print(f"{GREEN}OK{RESET} {msg}")


def fail(msg: str) -> None:
    print(f"{RED}FAIL{RESET} {msg}", file=sys.stderr)
    sys.exit(1)


def http_get(path: str) -> tuple[int, str]:
    req = urllib.request.Request(URL + path, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def http_post_json(path: str, payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        URL + path,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"raw": body}


BASE_MANDATE = {
    "mandate_id": "mnd_smoke01",
    "schema_version": "1.0",
    "status": "active",
    "issuer": {"org_id": "smoke", "user_id": "smoke"},
    "subject": {"agent_id": "smoke", "org_id": "smoke"},
    "scope": ["read:smoke"],
    "conditions": {},
    "policy_hash": None,
    "valid_from": "2026-01-01T00:00:00Z",
    "valid_until": "2030-01-01T00:00:00Z",
    "signatures": [],
    "revocation": None,
    "metadata": {},
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def check_health() -> None:
    print("> /health")
    code, _ = http_get("/health")
    if code != 200:
        fail(f"/health returned {code}")
    ok("/health 200")


def check_garbage_rejected() -> None:
    print("> /verify rejects garbage ECDSA signature")
    mandate = copy.deepcopy(BASE_MANDATE)
    mandate["mandate_id"] = "mnd_smoke_ecdsa"
    mandate["signatures"] = [
        {
            "algorithm": "ecdsa-p256-sha256",
            "key_id": "local:deadbeefdeadbeef",
            "signature": "AAAA",
        }
    ]
    code, body = http_post_json("/api/v1/mandates/verify", {"mandate": mandate})
    if code != 200:
        fail(f"/verify returned HTTP {code}: {body}")
    if body.get("valid") is not False:
        fail(f"verifier accepted a garbage mandate: {body}")
    err = (body.get("error") or "").lower()
    if "invalid" not in err:
        fail(f"expected error to mention invalid signatures, got: {body.get('error')!r}")
    ok("/verify rejects garbage ECDSA signature")


def check_ml_dsa_only_rejected() -> None:
    print("> /verify rejects ml-dsa-87-only mandate")
    mandate = copy.deepcopy(BASE_MANDATE)
    mandate["mandate_id"] = "mnd_smoke_pqc"
    mandate["signatures"] = [
        {
            "algorithm": "ml-dsa-87",
            "key_id": "kms:pqc-placeholder",
            "signature": "AAAA",
        }
    ]
    code, body = http_post_json("/api/v1/mandates/verify", {"mandate": mandate})
    if code != 200:
        fail(f"/verify returned HTTP {code}: {body}")
    if body.get("valid") is not False:
        fail(f"verifier accepted an ml-dsa-87-only mandate (regression!): {body}")
    err = body.get("error") or ""
    if "No verifiable signature algorithms" not in err:
        fail(f"expected error to mention 'No verifiable signature algorithms', got: {err!r}")
    ok("/verify rejects ml-dsa-87-only mandate")


def main() -> None:
    check_health()
    check_garbage_rejected()
    check_ml_dsa_only_rejected()
    print(f"{GREEN}Mandate Service smoke passed{RESET}")


if __name__ == "__main__":
    main()
