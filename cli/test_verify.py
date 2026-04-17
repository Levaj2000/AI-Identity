#!/usr/bin/env python3
"""Comprehensive tests for ai_identity_verify.py.

Uses only unittest (stdlib). Covers:
  - HMAC computation with known test vectors
  - Report verification (valid / tampered)
  - Chain verification (valid / broken / empty)
  - Missing environment variable handling
  - JSON and human-readable output modes
  - Edge cases (empty chain, single entry, cost_estimate_usd null)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import os
import sys
import tempfile
import unittest
from typing import Any
from unittest.mock import patch

# Import the CLI module from the same directory
sys.path.insert(0, os.path.dirname(__file__))
import contextlib

import ai_identity_verify as cli

# ── Test constants ──────────────────────────────────────────────────────

TEST_HMAC_KEY = "test-secret-key-for-verification"
TEST_HMAC_KEY_BYTES = TEST_HMAC_KEY.encode("utf-8")
TEST_AGENT_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_REPORT_ID = "fr-a1b2c3d4-20260310"
TEST_GENERATED_AT = "2026-04-08T21:10:37+00:00"


# ── Helpers ─────────────────────────────────────────────────────────────


def _make_report_signature(
    report_id: str = TEST_REPORT_ID,
    generated_at: str = TEST_GENERATED_AT,
    chain_valid: bool = True,
    total_entries: int = 3,
    entries_verified: int = 3,
    key: bytes = TEST_HMAC_KEY_BYTES,
) -> str:
    """Compute a report signature the same way the server does."""
    payload = json.dumps(
        {
            "entries_verified": entries_verified,
            "chain_valid": chain_valid,
            "generated_at": generated_at,
            "report_id": report_id,
            "total_entries": total_entries,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def _make_entry_hash(
    agent_id: str,
    endpoint: str,
    method: str,
    decision: str,
    cost_estimate_usd: Any,
    latency_ms: Any,
    request_metadata: dict,
    created_at: str,
    prev_hash: str,
    key: bytes = TEST_HMAC_KEY_BYTES,
) -> str:
    """Compute an entry hash the same way the server does."""
    payload = {
        "agent_id": str(agent_id),
        "cost_estimate_usd": str(cost_estimate_usd) if cost_estimate_usd is not None else None,
        "created_at": created_at,
        "decision": decision,
        "endpoint": endpoint,
        "latency_ms": latency_ms,
        "method": method,
        "prev_hash": prev_hash,
        "request_metadata": request_metadata,
    }
    message = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _build_chain(count: int = 3) -> list[dict[str, Any]]:
    """Build a valid chain of audit entries."""
    entries = []
    prev_hash = "GENESIS"
    for i in range(count):
        created_at = f"2026-04-08T10:{i:02d}:00+00:00"
        cost = 0.001 * (i + 1) if i % 2 == 0 else None
        latency = 50 + i * 10
        metadata = {"status_code": 200, "model": "gpt-4"}

        entry_hash = _make_entry_hash(
            agent_id=TEST_AGENT_ID,
            endpoint="/v1/chat/completions",
            method="POST",
            decision="allow",
            cost_estimate_usd=cost,
            latency_ms=latency,
            request_metadata=metadata,
            created_at=created_at,
            prev_hash=prev_hash,
        )
        entries.append(
            {
                "id": i + 1,
                "agent_id": TEST_AGENT_ID,
                "endpoint": "/v1/chat/completions",
                "method": "POST",
                "decision": "allow",
                "cost_estimate_usd": cost,
                "latency_ms": latency,
                "request_metadata": metadata,
                "created_at": created_at,
                "entry_hash": entry_hash,
                "prev_hash": prev_hash,
            }
        )
        prev_hash = entry_hash
    return entries


def _build_partial_chain(count: int = 3, start_id: int = 50) -> list[dict[str, Any]]:
    """Build a valid partial chain (first entry does NOT start at GENESIS).

    Simulates an export that starts mid-chain, e.g. from entry #50.
    """
    # Create a fake "previous hash" that would come from the entry before the export
    fake_prev = _make_entry_hash(
        agent_id=TEST_AGENT_ID,
        endpoint="/v1/chat/completions",
        method="POST",
        decision="allow",
        cost_estimate_usd=0.001,
        latency_ms=40,
        request_metadata={"status_code": 200},
        created_at="2026-04-08T09:59:00+00:00",
        prev_hash="GENESIS",
    )

    entries = []
    prev_hash = fake_prev
    for i in range(count):
        created_at = f"2026-04-08T10:{i:02d}:00+00:00"
        cost = 0.001 * (i + 1) if i % 2 == 0 else None
        latency = 50 + i * 10
        metadata = {"status_code": 200, "model": "gpt-4"}
        entry_id = start_id + i

        entry_hash = _make_entry_hash(
            agent_id=TEST_AGENT_ID,
            endpoint="/v1/chat/completions",
            method="POST",
            decision="allow",
            cost_estimate_usd=cost,
            latency_ms=latency,
            request_metadata=metadata,
            created_at=created_at,
            prev_hash=prev_hash,
        )
        entries.append(
            {
                "id": entry_id,
                "agent_id": TEST_AGENT_ID,
                "endpoint": "/v1/chat/completions",
                "method": "POST",
                "decision": "allow",
                "cost_estimate_usd": cost,
                "latency_ms": latency,
                "request_metadata": metadata,
                "created_at": created_at,
                "entry_hash": entry_hash,
                "prev_hash": prev_hash,
            }
        )
        prev_hash = entry_hash
    return entries


def _build_report(entries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Build a valid ForensicsReportResponse-shaped dict."""
    if entries is None:
        entries = _build_chain(3)
    total = len(entries)
    sig = _make_report_signature(
        total_entries=total,
        entries_verified=total,
    )
    return {
        "report_id": TEST_REPORT_ID,
        "generated_at": TEST_GENERATED_AT,
        "events": entries,
        "chain_verification": {
            "valid": True,
            "chain_valid": True,
            "total_entries": total,
            "entries_verified": total,
            "message": "Chain integrity verified",
        },
        "report_signature": sig,
    }


def _write_json(data: Any) -> str:
    """Write data to a temporary JSON file, returning the path."""
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


def _run_cmd(argv: list[str], env_key: str = TEST_HMAC_KEY) -> tuple[int, str, str]:
    """Run the CLI main() capturing stdout/stderr and return (exit_code, stdout, stderr)."""
    env_patch = {"AI_IDENTITY_HMAC_KEY": env_key} if env_key else {}
    stdout = io.StringIO()
    stderr = io.StringIO()
    with (
        patch.dict(os.environ, env_patch, clear=False),
        patch("sys.stdout", stdout),
        patch("sys.stderr", stderr),
    ):
        # Remove key if env_key is explicitly empty string
        if env_key == "":
            os.environ.pop("AI_IDENTITY_HMAC_KEY", None)
        try:
            code = cli.main(argv)
        except SystemExit as e:
            code = e.code if e.code is not None else 0
    return code, stdout.getvalue(), stderr.getvalue()


# ── Test: Known HMAC test vectors ───────────────────────────────────────


class TestHMACVectors(unittest.TestCase):
    """Verify that HMAC computations produce expected deterministic output."""

    def test_report_signature_known_vector(self):
        """Compute a report signature and verify it matches a known value."""
        sig = _make_report_signature(
            report_id="test-report-001",
            generated_at="2026-01-01T00:00:00+00:00",
            chain_valid=True,
            total_entries=10,
            entries_verified=10,
            key=b"known-test-key",
        )
        # Recompute the same way
        payload = json.dumps(
            {
                "entries_verified": 10,
                "chain_valid": True,
                "generated_at": "2026-01-01T00:00:00+00:00",
                "report_id": "test-report-001",
                "total_entries": 10,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        expected = hmac.new(b"known-test-key", payload, hashlib.sha256).hexdigest()
        self.assertEqual(sig, expected)
        # Deterministic — same inputs always produce same output
        sig2 = _make_report_signature(
            report_id="test-report-001",
            generated_at="2026-01-01T00:00:00+00:00",
            chain_valid=True,
            total_entries=10,
            entries_verified=10,
            key=b"known-test-key",
        )
        self.assertEqual(sig, sig2)

    def test_entry_hash_known_vector(self):
        """Compute an entry hash and verify deterministic output."""
        h1 = _make_entry_hash(
            agent_id=TEST_AGENT_ID,
            endpoint="/test",
            method="GET",
            decision="allow",
            cost_estimate_usd=None,
            latency_ms=42,
            request_metadata={},
            created_at="2026-01-01T00:00:00+00:00",
            prev_hash="GENESIS",
        )
        h2 = _make_entry_hash(
            agent_id=TEST_AGENT_ID,
            endpoint="/test",
            method="GET",
            decision="allow",
            cost_estimate_usd=None,
            latency_ms=42,
            request_metadata={},
            created_at="2026-01-01T00:00:00+00:00",
            prev_hash="GENESIS",
        )
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)  # SHA-256 hex digest

    def test_different_key_produces_different_hash(self):
        """Different HMAC keys produce different results."""
        h1 = _make_entry_hash(
            agent_id=TEST_AGENT_ID,
            endpoint="/test",
            method="GET",
            decision="allow",
            cost_estimate_usd=None,
            latency_ms=10,
            request_metadata={},
            created_at="2026-01-01T00:00:00+00:00",
            prev_hash="GENESIS",
            key=b"key-one",
        )
        h2 = _make_entry_hash(
            agent_id=TEST_AGENT_ID,
            endpoint="/test",
            method="GET",
            decision="allow",
            cost_estimate_usd=None,
            latency_ms=10,
            request_metadata={},
            created_at="2026-01-01T00:00:00+00:00",
            prev_hash="GENESIS",
            key=b"key-two",
        )
        self.assertNotEqual(h1, h2)

    def test_canonical_sort_order(self):
        """Canonical payload sorts keys alphabetically."""
        payload = cli._canonical_entry_payload(
            {
                "agent_id": TEST_AGENT_ID,
                "endpoint": "/v1/test",
                "method": "POST",
                "decision": "allow",
                "cost_estimate_usd": 0.05,
                "latency_ms": 100,
                "request_metadata": {"a": 1},
                "created_at": "2026-01-01T00:00:00+00:00",
            },
            "GENESIS",
        )
        decoded = json.loads(payload)
        keys = list(decoded.keys())
        self.assertEqual(keys, sorted(keys))

    def test_cost_estimate_string_conversion(self):
        """cost_estimate_usd is converted to string in payload."""
        payload = cli._canonical_entry_payload(
            {
                "agent_id": TEST_AGENT_ID,
                "endpoint": "/test",
                "method": "GET",
                "decision": "allow",
                "cost_estimate_usd": 0.123,
                "latency_ms": None,
                "request_metadata": {},
                "created_at": "2026-01-01T00:00:00+00:00",
            },
            "GENESIS",
        )
        decoded = json.loads(payload)
        self.assertEqual(decoded["cost_estimate_usd"], "0.123")

    def test_cost_estimate_null_stays_null(self):
        """cost_estimate_usd=None stays null in payload."""
        payload = cli._canonical_entry_payload(
            {
                "agent_id": TEST_AGENT_ID,
                "endpoint": "/test",
                "method": "GET",
                "decision": "allow",
                "cost_estimate_usd": None,
                "latency_ms": None,
                "request_metadata": {},
                "created_at": "2026-01-01T00:00:00+00:00",
            },
            "GENESIS",
        )
        decoded = json.loads(payload)
        self.assertIsNone(decoded["cost_estimate_usd"])


# ── Test: Report verification ───────────────────────────────────────────


class TestReportVerification(unittest.TestCase):
    """Test the report subcommand."""

    def test_valid_report(self):
        """A correctly signed report returns exit code 0."""
        report = _build_report()
        path = _write_json(report)
        try:
            code, out, err = _run_cmd(["--no-color", "report", path])
            self.assertEqual(code, 0)
            self.assertIn("VALID", out)
        finally:
            os.unlink(path)

    def test_valid_report_json_output(self):
        """JSON output for a valid report includes signature_valid=true."""
        report = _build_report()
        path = _write_json(report)
        try:
            code, out, err = _run_cmd(["--json", "report", path])
            self.assertEqual(code, 0)
            result = json.loads(out)
            self.assertEqual(result["result"], "valid")
            self.assertTrue(result["details"]["signature_valid"])
        finally:
            os.unlink(path)

    def test_tampered_report_id(self):
        """Changing the report_id invalidates the signature."""
        report = _build_report()
        report["report_id"] = "tampered-id"
        path = _write_json(report)
        try:
            code, out, err = _run_cmd(["--no-color", "report", path])
            self.assertEqual(code, 1)
            self.assertIn("INVALID", out)
        finally:
            os.unlink(path)

    def test_tampered_entries_count(self):
        """Changing total_entries invalidates the signature."""
        report = _build_report()
        report["chain_verification"]["total_entries"] = 9999
        path = _write_json(report)
        try:
            code, out, err = _run_cmd(["--no-color", "report", path])
            self.assertEqual(code, 1)
        finally:
            os.unlink(path)

    def test_tampered_signature(self):
        """A corrupted signature string is detected."""
        report = _build_report()
        report["report_signature"] = "0" * 64
        path = _write_json(report)
        try:
            code, out, err = _run_cmd(["--no-color", "report", path])
            self.assertEqual(code, 1)
        finally:
            os.unlink(path)

    def test_tampered_chain_valid_flag(self):
        """Flipping chain_valid from true to false is detected."""
        report = _build_report()
        report["chain_verification"]["chain_valid"] = False
        path = _write_json(report)
        try:
            code, out, err = _run_cmd(["--no-color", "report", path])
            self.assertEqual(code, 1)
        finally:
            os.unlink(path)

    def test_wrong_hmac_key(self):
        """Using the wrong HMAC key produces an invalid result."""
        report = _build_report()
        path = _write_json(report)
        try:
            code, out, err = _run_cmd(["--no-color", "report", path], env_key="wrong-key")
            self.assertEqual(code, 1)
        finally:
            os.unlink(path)

    def test_missing_fields(self):
        """A JSON file missing required fields exits with code 2."""
        path = _write_json({"some": "data"})
        try:
            code, out, err = _run_cmd(["report", path])
            self.assertEqual(code, 2)
            self.assertIn("missing", err.lower())
        finally:
            os.unlink(path)

    def test_verbose_shows_hashes(self):
        """Verbose mode shows expected and actual hashes."""
        report = _build_report()
        path = _write_json(report)
        try:
            code, out, err = _run_cmd(["--no-color", "--verbose", "report", path])
            self.assertEqual(code, 0)
            self.assertIn("Expected:", out)
            self.assertIn("Got:", out)
        finally:
            os.unlink(path)


# ── Test: Chain verification ────────────────────────────────────────────


class TestChainVerification(unittest.TestCase):
    """Test the chain subcommand."""

    def test_valid_chain(self):
        """A valid chain returns exit code 0."""
        entries = _build_chain(5)
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--no-color", "chain", path])
            self.assertEqual(code, 0)
            self.assertIn("CHAIN INTACT", out)
            self.assertIn("5/5", out)
        finally:
            os.unlink(path)

    def test_valid_chain_json(self):
        """JSON output for a valid chain."""
        entries = _build_chain(3)
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--json", "chain", path])
            self.assertEqual(code, 0)
            result = json.loads(out)
            self.assertEqual(result["result"], "valid")
            self.assertTrue(result["details"]["chain_intact"])
            self.assertEqual(result["details"]["entries_verified"], 3)
        finally:
            os.unlink(path)

    def test_tampered_entry_hash(self):
        """Tampering with an entry_hash breaks the chain."""
        entries = _build_chain(5)
        entries[2]["entry_hash"] = "0" * 64  # corrupt middle entry
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--no-color", "chain", path])
            self.assertEqual(code, 1)
            self.assertIn("CHAIN BROKEN", out)
            self.assertIn("2/5", out)  # only first 2 verified
        finally:
            os.unlink(path)

    def test_tampered_entry_data(self):
        """Changing an entry's data field breaks the chain at that entry."""
        entries = _build_chain(5)
        entries[1]["decision"] = "deny"  # tamper with data
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--no-color", "chain", path])
            self.assertEqual(code, 1)
            self.assertIn("CHAIN BROKEN", out)
            self.assertIn("1/5", out)  # only first entry verified
        finally:
            os.unlink(path)

    def test_tampered_prev_hash(self):
        """Changing prev_hash breaks the chain."""
        entries = _build_chain(3)
        entries[1]["prev_hash"] = "bad" * 21 + "x"  # wrong prev link
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--no-color", "chain", path])
            self.assertEqual(code, 1)
            self.assertIn("CHAIN BROKEN", out)
        finally:
            os.unlink(path)

    def test_deleted_entry(self):
        """Removing an entry from the middle breaks the chain."""
        entries = _build_chain(5)
        del entries[2]  # remove middle entry
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--no-color", "chain", path])
            self.assertEqual(code, 1)
            self.assertIn("CHAIN BROKEN", out)
        finally:
            os.unlink(path)

    def test_empty_chain(self):
        """An empty chain returns exit code 0."""
        path = _write_json([])
        try:
            code, out, err = _run_cmd(["--no-color", "chain", path])
            self.assertEqual(code, 0)
        finally:
            os.unlink(path)

    def test_single_entry_chain(self):
        """A single valid entry chain verifies correctly."""
        entries = _build_chain(1)
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--no-color", "chain", path])
            self.assertEqual(code, 0)
            self.assertIn("1/1", out)
        finally:
            os.unlink(path)

    def test_chain_in_report_envelope(self):
        """Chain command extracts entries from a report-shaped JSON."""
        report = _build_report(_build_chain(3))
        path = _write_json(report)
        try:
            code, out, err = _run_cmd(["--no-color", "chain", path])
            self.assertEqual(code, 0)
            self.assertIn("CHAIN INTACT", out)
        finally:
            os.unlink(path)

    def test_wrong_key_breaks_chain(self):
        """Using the wrong HMAC key breaks chain verification."""
        entries = _build_chain(3)
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--no-color", "chain", path], env_key="wrong-key")
            self.assertEqual(code, 1)
            self.assertIn("CHAIN BROKEN", out)
        finally:
            os.unlink(path)

    def test_chain_json_broken(self):
        """JSON output for a broken chain includes break_at details."""
        entries = _build_chain(5)
        entries[3]["decision"] = "deny"
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--json", "chain", path])
            self.assertEqual(code, 1)
            result = json.loads(out)
            self.assertEqual(result["result"], "broken")
            self.assertFalse(result["details"]["chain_intact"])
            self.assertIn("break_at", result["details"])
            self.assertEqual(result["details"]["break_at"]["index"], 3)
        finally:
            os.unlink(path)


# ── Test: Partial chain verification ──────────────────────────────────


class TestPartialChainVerification(unittest.TestCase):
    """Test partial chain verification (entries not starting from genesis)."""

    def test_single_entry_valid(self):
        """A single valid partial entry returns exit code 0 and ENTRY VERIFIED."""
        entries = _build_partial_chain(count=1, start_id=96)
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--no-color", "chain", path])
            self.assertEqual(code, 0)
            self.assertIn("ENTRY VERIFIED", out)
            self.assertIn("1/1", out)
            self.assertIn("Partial", out)
            self.assertIn("entry #96", out)
            self.assertIn("Entry hash matches HMAC computation", out)
            self.assertIn("Chain linkage cannot be fully verified", out)
        finally:
            os.unlink(path)

    def test_single_entry_tampered(self):
        """A tampered single partial entry returns exit code 1 and ENTRY TAMPERED."""
        entries = _build_partial_chain(count=1, start_id=96)
        entries[0]["decision"] = "deny"  # tamper with data
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--no-color", "chain", path])
            self.assertEqual(code, 1)
            self.assertIn("ENTRY TAMPERED", out)
            self.assertIn("0/1", out)
            self.assertIn("Entry #96", out)
        finally:
            os.unlink(path)

    def test_multi_entry_partial_chain_valid(self):
        """A valid multi-entry partial chain returns exit code 0 and PARTIAL CHAIN INTACT."""
        entries = _build_partial_chain(count=5, start_id=50)
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--no-color", "chain", path])
            self.assertEqual(code, 0)
            self.assertIn("PARTIAL CHAIN INTACT", out)
            self.assertIn("5/5", out)
            self.assertIn("Partial", out)
            self.assertIn("entry #50", out)
            self.assertIn("All entry hashes valid and chain linkage", out)
        finally:
            os.unlink(path)

    def test_multi_entry_partial_chain_tampered(self):
        """A tampered entry in a partial chain returns exit code 1."""
        entries = _build_partial_chain(count=5, start_id=50)
        entries[2]["entry_hash"] = "0" * 64  # corrupt middle entry
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--no-color", "chain", path])
            self.assertEqual(code, 1)
            self.assertIn("TAMPERED", out)
        finally:
            os.unlink(path)

    def test_partial_chain_json_output(self):
        """JSON output for partial chain includes mode=partial."""
        entries = _build_partial_chain(count=3, start_id=50)
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--json", "chain", path])
            self.assertEqual(code, 0)
            result = json.loads(out)
            self.assertEqual(result["result"], "partial_valid")
            self.assertEqual(result["details"]["mode"], "partial")
            self.assertTrue(result["details"]["chain_intact"])
            self.assertEqual(result["details"]["entries_verified"], 3)
            self.assertEqual(result["details"]["partial_start_entry"], 50)
        finally:
            os.unlink(path)

    def test_single_entry_tampered_json_output(self):
        """JSON output for a tampered partial entry includes mode=partial and tampered info."""
        entries = _build_partial_chain(count=1, start_id=96)
        entries[0]["decision"] = "deny"
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--json", "chain", path])
            self.assertEqual(code, 1)
            result = json.loads(out)
            self.assertEqual(result["result"], "entry_tampered")
            self.assertEqual(result["details"]["mode"], "partial")
            self.assertFalse(result["details"]["chain_intact"])
            self.assertEqual(result["details"]["entries_verified"], 0)
            self.assertIn("tampered_entries", result["details"])
        finally:
            os.unlink(path)

    def test_full_chain_still_works(self):
        """A full chain (starting at GENESIS) still works with the existing logic."""
        entries = _build_chain(5)
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--json", "chain", path])
            self.assertEqual(code, 0)
            result = json.loads(out)
            self.assertEqual(result["details"]["mode"], "full")
            self.assertTrue(result["details"]["chain_intact"])
        finally:
            os.unlink(path)

    def test_full_chain_broken_still_detected(self):
        """A broken full chain is still detected correctly."""
        entries = _build_chain(5)
        entries[2]["decision"] = "deny"
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--json", "chain", path])
            self.assertEqual(code, 1)
            result = json.loads(out)
            self.assertEqual(result["details"]["mode"], "full")
            self.assertEqual(result["result"], "broken")
        finally:
            os.unlink(path)

    def test_expected_prev_hash_valid_anchor(self):
        """--expected-prev-hash matches the first entry's prev_hash: anchor_verified=True, exit 0."""
        entries = _build_partial_chain(count=3, start_id=50)
        known_prev = entries[0]["prev_hash"]
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--json", "chain", path, "--expected-prev-hash", known_prev])
            self.assertEqual(code, 0)
            result = json.loads(out)
            self.assertTrue(result["details"]["anchor_verified"])
            self.assertEqual(result["result"], "partial_valid")
        finally:
            os.unlink(path)

    def test_expected_prev_hash_wrong_anchor(self):
        """--expected-prev-hash mismatch: anchor_verified=False, exit 1 even if entries are valid."""
        entries = _build_partial_chain(count=3, start_id=50)
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--json", "chain", path, "--expected-prev-hash", "a" * 64])
            self.assertEqual(code, 1)
            result = json.loads(out)
            self.assertFalse(result["details"]["anchor_verified"])
        finally:
            os.unlink(path)

    def test_expected_prev_hash_not_supplied(self):
        """Without --expected-prev-hash, anchor_verified is absent from output."""
        entries = _build_partial_chain(count=2, start_id=10)
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--json", "chain", path])
            self.assertEqual(code, 0)
            result = json.loads(out)
            self.assertNotIn("anchor_verified", result["details"])
        finally:
            os.unlink(path)


# ── Test: Environment variable handling ─────────────────────────────────


class TestEnvVarHandling(unittest.TestCase):
    """Test missing/empty HMAC key behaviour."""

    def test_missing_env_var_report(self):
        """Missing AI_IDENTITY_HMAC_KEY exits with code 2 and clear message."""
        report = _build_report()
        path = _write_json(report)
        try:
            env = os.environ.copy()
            env.pop("AI_IDENTITY_HMAC_KEY", None)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                patch.dict(os.environ, env, clear=True),
                patch("sys.stdout", stdout),
                patch("sys.stderr", stderr),
            ):
                try:
                    cli.main(["report", path])
                except SystemExit as e:
                    code = e.code
            self.assertEqual(code, 2)
            self.assertIn("AI_IDENTITY_HMAC_KEY", stderr.getvalue())
        finally:
            os.unlink(path)

    def test_missing_env_var_chain(self):
        """Missing key for chain command also exits with code 2."""
        entries = _build_chain(1)
        path = _write_json(entries)
        try:
            env = os.environ.copy()
            env.pop("AI_IDENTITY_HMAC_KEY", None)
            stderr = io.StringIO()
            with (
                patch.dict(os.environ, env, clear=True),
                patch("sys.stdout", io.StringIO()),
                patch("sys.stderr", stderr),
            ):
                try:
                    cli.main(["chain", path])
                except SystemExit as e:
                    code = e.code
            self.assertEqual(code, 2)
            self.assertIn("AI_IDENTITY_HMAC_KEY", stderr.getvalue())
        finally:
            os.unlink(path)


# ── Test: CLI argument parsing ──────────────────────────────────────────


class TestCLIParsing(unittest.TestCase):
    """Test CLI argument parsing edge cases."""

    def test_no_command_shows_help(self):
        """No subcommand exits with code 2."""
        code, out, err = _run_cmd([])
        self.assertEqual(code, 2)

    def test_invalid_json_file(self):
        """An invalid JSON file exits with code 2."""
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            f.write("not valid json{{{")
        try:
            code, out, err = _run_cmd(["report", path])
            self.assertEqual(code, 2)
            self.assertIn("Invalid JSON", err)
        finally:
            os.unlink(path)

    def test_nonexistent_file(self):
        """A nonexistent file exits with code 2."""
        code, out, err = _run_cmd(["report", "/tmp/nonexistent_file_12345.json"])
        self.assertEqual(code, 2)
        self.assertIn("not found", err.lower())

    def test_version_flag(self):
        """--version prints version."""
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch("sys.stdout", stdout),
            patch("sys.stderr", stderr),
            contextlib.suppress(SystemExit),
        ):
            cli.main(["--version"])
        combined = stdout.getvalue() + stderr.getvalue()
        self.assertIn(cli.__version__, combined)


# ── Test: Cross-validation with server logic ────────────────────────────


class TestServerCompatibility(unittest.TestCase):
    """Ensure CLI computations match the server implementation exactly."""

    def test_report_payload_canonical_form(self):
        """Canonical report payload matches expected JSON string."""
        payload = cli._canonical_report_payload(
            report_id="rpt-001",
            generated_at="2026-01-01T00:00:00+00:00",
            chain_valid=True,
            total_entries=5,
            entries_verified=5,
        )
        # Decode and verify structure
        decoded = json.loads(payload)
        keys = list(decoded.keys())
        self.assertEqual(keys, sorted(keys), "Keys must be alphabetically sorted")
        # No spaces in compact format
        self.assertNotIn(": ", payload.decode())
        self.assertNotIn(", ", payload.decode())

    def test_entry_payload_canonical_form(self):
        """Canonical entry payload matches server's _canonical_payload."""
        payload = cli._canonical_entry_payload(
            {
                "agent_id": TEST_AGENT_ID,
                "endpoint": "/v1/chat/completions",
                "method": "POST",
                "decision": "allow",
                "cost_estimate_usd": 0.05,
                "latency_ms": 100,
                "request_metadata": {"model": "gpt-4"},
                "created_at": "2026-04-08T10:00:00+00:00",
            },
            "GENESIS",
        )
        decoded = json.loads(payload)
        # Verify the exact same fields the server includes
        expected_keys = [
            "agent_id",
            "cost_estimate_usd",
            "created_at",
            "decision",
            "endpoint",
            "latency_ms",
            "method",
            "prev_hash",
            "request_metadata",
        ]
        self.assertEqual(list(decoded.keys()), expected_keys)
        # cost_estimate_usd as string
        self.assertEqual(decoded["cost_estimate_usd"], "0.05")
        # prev_hash included
        self.assertEqual(decoded["prev_hash"], "GENESIS")

    def test_genesis_constant(self):
        """GENESIS sentinel matches server constant."""
        self.assertEqual(cli.GENESIS, "GENESIS")

    def test_chain_links_correctly(self):
        """Each entry's prev_hash equals the previous entry's entry_hash."""
        entries = _build_chain(5)
        self.assertEqual(entries[0]["prev_hash"], "GENESIS")
        for i in range(1, len(entries)):
            self.assertEqual(
                entries[i]["prev_hash"],
                entries[i - 1]["entry_hash"],
                f"Entry {i} prev_hash should equal entry {i - 1} entry_hash",
            )


# ── Test: Timestamp normalization (Z vs +00:00) ──────────────────────────


class TestTimestampNormalization(unittest.TestCase):
    """Verify that Z-suffix timestamps produce the same HMAC as +00:00."""

    def test_normalize_z_to_offset(self):
        """_normalize_timestamp converts Z to +00:00."""
        self.assertEqual(
            cli._normalize_timestamp("2026-04-06T15:33:58.228487Z"),
            "2026-04-06T15:33:58.228487+00:00",
        )

    def test_normalize_already_offset(self):
        """_normalize_timestamp is a no-op for +00:00."""
        ts = "2026-04-06T15:33:58.228487+00:00"
        self.assertEqual(cli._normalize_timestamp(ts), ts)

    def test_normalize_no_tz(self):
        """_normalize_timestamp is a no-op for timestamps without timezone."""
        ts = "2026-04-06T15:33:58.228487"
        self.assertEqual(cli._normalize_timestamp(ts), ts)

    def test_entry_hash_z_matches_offset(self):
        """An entry with Z timestamp produces the same hash as +00:00."""
        entry_z = {
            "agent_id": TEST_AGENT_ID,
            "endpoint": "/v1/chat/completions",
            "method": "POST",
            "decision": "allow",
            "cost_estimate_usd": 0.001,
            "latency_ms": 50,
            "request_metadata": {"status_code": 200},
            "created_at": "2026-04-06T15:33:58.228487Z",
        }
        entry_offset = dict(entry_z, created_at="2026-04-06T15:33:58.228487+00:00")

        hash_z = cli._compute_entry_hash(TEST_HMAC_KEY_BYTES, entry_z, "GENESIS")
        hash_offset = cli._compute_entry_hash(TEST_HMAC_KEY_BYTES, entry_offset, "GENESIS")
        self.assertEqual(hash_z, hash_offset)

    def test_report_signature_z_matches_offset(self):
        """A report with Z generated_at produces the same signature as +00:00."""
        sig_z = cli._compute_report_signature(
            TEST_HMAC_KEY_BYTES,
            report_id="rpt-001",
            generated_at="2026-04-08T21:10:37Z",
            chain_valid=True,
            total_entries=3,
            entries_verified=3,
        )
        sig_offset = cli._compute_report_signature(
            TEST_HMAC_KEY_BYTES,
            report_id="rpt-001",
            generated_at="2026-04-08T21:10:37+00:00",
            chain_valid=True,
            total_entries=3,
            entries_verified=3,
        )
        self.assertEqual(sig_z, sig_offset)

    def test_chain_with_z_timestamps_verifies(self):
        """A full chain exported with Z timestamps verifies correctly."""
        # Build a chain with +00:00 (server-side), then convert to Z (JSON export)
        entries = _build_chain(3)
        for e in entries:
            e["created_at"] = e["created_at"].replace("+00:00", "Z")
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--no-color", "chain", path])
            self.assertEqual(code, 0)
            self.assertIn("CHAIN INTACT", out)
        finally:
            os.unlink(path)

    def test_partial_chain_with_z_timestamps_verifies(self):
        """A partial chain exported with Z timestamps verifies correctly."""
        entries = _build_partial_chain(count=3, start_id=50)
        for e in entries:
            e["created_at"] = e["created_at"].replace("+00:00", "Z")
        path = _write_json(entries)
        try:
            code, out, err = _run_cmd(["--no-color", "chain", path])
            self.assertEqual(code, 0)
            self.assertIn("PARTIAL CHAIN INTACT", out)
        finally:
            os.unlink(path)

    def test_report_with_z_generated_at_verifies(self):
        """A report exported with Z generated_at verifies correctly."""
        report = _build_report()
        report["generated_at"] = report["generated_at"].replace("+00:00", "Z")
        path = _write_json(report)
        try:
            code, out, err = _run_cmd(["--no-color", "report", path])
            self.assertEqual(code, 0)
            self.assertIn("VALID", out)
        finally:
            os.unlink(path)


# ── Attestation verification tests ──────────────────────────────────────


def _have_cryptography() -> bool:
    try:
        import cryptography  # noqa: F401
    except ImportError:
        return False
    return True


@unittest.skipUnless(_have_cryptography(), "cryptography package not installed")
class TestAttestationVerification(unittest.TestCase):
    """End-to-end tests for the `attestation` subcommand.

    These tests import the server-side signer helpers so the signed
    envelope we hand to the CLI is produced exactly the same way
    production signs — no divergent mock implementation.
    """

    @classmethod
    def setUpClass(cls):
        # Make the project importable so we can reuse the server signer.
        import pathlib

        repo_root = pathlib.Path(__file__).resolve().parent.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        import uuid
        from datetime import datetime as _dt
        from datetime import timezone as _tz

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec

        from common.schemas.forensic_attestation import (
            AttestationPayloadV1,
            local_ecdsa_signer,
            sign_payload,
        )

        cls._uuid = uuid
        cls._dt = _dt
        cls._tz = _tz
        cls._AttestationPayloadV1 = AttestationPayloadV1
        # Wrap callables in staticmethod so Python doesn't try to bind
        # them to `self` when accessed via instance attribute lookup.
        cls._sign_payload = staticmethod(sign_payload)
        cls._local_ecdsa_signer = staticmethod(local_ecdsa_signer)
        cls._serialization = serialization
        cls._ec = ec

        # Fresh keypair for the whole suite — the envelope and JWKS
        # always agree on key identity.
        cls._private_key = ec.generate_private_key(ec.SECP256R1())
        cls._pub_pem = cls._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        import hashlib as _hashlib

        pub_der = cls._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        cls._kid = "local:" + _hashlib.sha256(pub_der).hexdigest()

    # Factories ---------------------------------------------------------

    def _build_envelope(self, *, kid: str | None = None) -> dict[str, Any]:
        now = self._dt.now(self._tz.utc)
        payload = self._AttestationPayloadV1(
            session_id=self._uuid.UUID("b8f2c1a0-4e6d-4e2a-9f1a-3c2b0d4e8f7a"),
            org_id=self._uuid.UUID("f1e2d3c4-b5a6-4798-8877-66554433abcd"),
            evidence_chain_hash="3b7e0a6f4a9d8c2e5b1f0d3c6a8b9e2d1f4c7a0b3d6e9f2a5c8b1d4e7a0b3c6d",
            first_audit_id=104821,
            last_audit_id=104827,
            event_count=7,
            session_start=now,
            session_end=now,
            signed_at=now,
            signer_key_id=kid or self._kid,
        )
        envelope = self._sign_payload(payload, self._local_ecdsa_signer(self._private_key))
        return envelope.model_dump()

    def _write_pem(self, pem_bytes: bytes) -> str:
        fd, path = tempfile.mkstemp(suffix=".pem")
        with os.fdopen(fd, "wb") as f:
            f.write(pem_bytes)
        return path

    def _write_jwks(self, kid: str, pub_pem: bytes) -> str:
        """Build a minimal JWKS containing one EC P-256 entry."""
        public_key = self._serialization.load_pem_public_key(pub_pem)
        nums = public_key.public_numbers()
        x_b = nums.x.to_bytes(32, "big")
        y_b = nums.y.to_bytes(32, "big")
        jwks = {
            "keys": [
                {
                    "kty": "EC",
                    "crv": "P-256",
                    "x": base64.urlsafe_b64encode(x_b).rstrip(b"=").decode(),
                    "y": base64.urlsafe_b64encode(y_b).rstrip(b"=").decode(),
                    "kid": kid,
                    "alg": "ES256",
                    "use": "sig",
                }
            ]
        }
        return _write_json(jwks)

    # Tests -------------------------------------------------------------

    def test_valid_envelope_with_pubkey(self):
        envelope_path = _write_json(self._build_envelope())
        pub_path = self._write_pem(self._pub_pem)
        try:
            code, out, err = _run_cmd(
                ["--no-color", "attestation", envelope_path, "--pubkey", pub_path]
            )
            self.assertEqual(code, 0, msg=err)
            self.assertIn("VALID", out)
            self.assertIn("Audit range:", out)
        finally:
            os.unlink(envelope_path)
            os.unlink(pub_path)

    def test_valid_envelope_with_jwks(self):
        envelope_path = _write_json(self._build_envelope())
        jwks_path = self._write_jwks(self._kid, self._pub_pem)
        try:
            code, out, err = _run_cmd(
                ["--no-color", "attestation", envelope_path, "--jwks", jwks_path]
            )
            self.assertEqual(code, 0, msg=err)
            self.assertIn("VALID", out)
        finally:
            os.unlink(envelope_path)
            os.unlink(jwks_path)

    def test_tampered_payload_fails(self):
        """Re-encode the payload with a changed field but keep the original
        signature → signature check must reject it.

        We mutate inside a value (not a structural byte) so JSON parsing
        still succeeds and the CLI reaches the ECDSA verify step.
        """
        envelope = self._build_envelope()
        raw = base64.b64decode(envelope["payload"])
        payload_json = json.loads(raw)
        payload_json["event_count"] = payload_json["event_count"] + 1
        envelope["payload"] = base64.b64encode(
            json.dumps(payload_json, separators=(",", ":")).encode("utf-8")
        ).decode()
        envelope_path = _write_json(envelope)
        pub_path = self._write_pem(self._pub_pem)
        try:
            code, out, _err = _run_cmd(
                ["--no-color", "attestation", envelope_path, "--pubkey", pub_path]
            )
            self.assertEqual(code, 1)
            self.assertIn("INVALID", out)
        finally:
            os.unlink(envelope_path)
            os.unlink(pub_path)

    def test_wrong_pubkey_fails(self):
        """Correct envelope, different key → signature invalid."""
        envelope_path = _write_json(self._build_envelope())
        other_key = self._ec.generate_private_key(self._ec.SECP256R1())
        other_pem = other_key.public_key().public_bytes(
            encoding=self._serialization.Encoding.PEM,
            format=self._serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        pub_path = self._write_pem(other_pem)
        try:
            code, out, _err = _run_cmd(
                ["--no-color", "attestation", envelope_path, "--pubkey", pub_path]
            )
            self.assertEqual(code, 1)
            self.assertIn("INVALID", out)
        finally:
            os.unlink(envelope_path)
            os.unlink(pub_path)

    def test_unknown_kid_in_jwks(self):
        """JWKS has no entry for the envelope's kid → exit 1 with useful msg."""
        envelope_path = _write_json(self._build_envelope())
        # JWKS advertises a different kid for the same key
        jwks_path = self._write_jwks("local:wrong-kid", self._pub_pem)
        try:
            code, _out, err = _run_cmd(
                ["--no-color", "attestation", envelope_path, "--jwks", jwks_path]
            )
            self.assertEqual(code, 1)
            self.assertIn("no key with kid", err)
        finally:
            os.unlink(envelope_path)
            os.unlink(jwks_path)

    def test_wrong_schema_version_rejected(self):
        """A v2 envelope must be rejected by a v1 CLI, not silently accepted."""
        envelope = self._build_envelope()
        # Rebuild the payload with schema_version=2 and re-base64 (no
        # re-sign needed — the test checks that schema is validated
        # before the signature would even pass).
        payload_bytes = base64.b64decode(envelope["payload"])
        payload_json = json.loads(payload_bytes)
        payload_json["schema_version"] = 2
        envelope["payload"] = base64.b64encode(
            json.dumps(payload_json, separators=(",", ":")).encode()
        ).decode()
        envelope_path = _write_json(envelope)
        pub_path = self._write_pem(self._pub_pem)
        try:
            code, _out, err = _run_cmd(
                ["--no-color", "attestation", envelope_path, "--pubkey", pub_path]
            )
            self.assertEqual(code, 1)
            self.assertIn("Unsupported schema_version", err)
        finally:
            os.unlink(envelope_path)
            os.unlink(pub_path)

    def test_bad_payload_type_rejected(self):
        """Non-attestation DSSE envelope is rejected with exit 1."""
        envelope = self._build_envelope()
        envelope["payloadType"] = "application/vnd.other+json"
        envelope_path = _write_json(envelope)
        pub_path = self._write_pem(self._pub_pem)
        try:
            code, _out, err = _run_cmd(
                ["--no-color", "attestation", envelope_path, "--pubkey", pub_path]
            )
            self.assertEqual(code, 1)
            self.assertIn("Unexpected payloadType", err)
        finally:
            os.unlink(envelope_path)
            os.unlink(pub_path)

    def test_missing_key_source_usage_error(self):
        envelope_path = _write_json(self._build_envelope())
        try:
            code, _out, err = _run_cmd(["--no-color", "attestation", envelope_path])
            self.assertEqual(code, 2)
            self.assertIn("--pubkey", err)
            self.assertIn("--jwks", err)
        finally:
            os.unlink(envelope_path)

    def test_json_output_valid(self):
        envelope_path = _write_json(self._build_envelope())
        pub_path = self._write_pem(self._pub_pem)
        try:
            code, out, _err = _run_cmd(
                [
                    "--no-color",
                    "--json",
                    "attestation",
                    envelope_path,
                    "--pubkey",
                    pub_path,
                ]
            )
            self.assertEqual(code, 0)
            parsed = json.loads(out)
            self.assertEqual(parsed["result"], "valid")
            self.assertEqual(parsed["command"], "attestation")
            self.assertTrue(parsed["details"]["signature_valid"])
            self.assertEqual(parsed["details"]["event_count"], 7)
        finally:
            os.unlink(envelope_path)
            os.unlink(pub_path)


if __name__ == "__main__":
    unittest.main()
