"""Tests for the OCSF API Activity mapping (audit_log → class_uid 6003).

Grounds the export against AI Identity's OCSF contributions: API Activity +
ai_operation profile (#1641), the attestation integrity object (#1661), and
honest ``unmapped`` placement for producer facts with no native home.
"""

import datetime
import types

from common.ocsf import OCSF_VERSION, audit_log_to_ocsf


def _row(**overrides):
    base = dict(
        id=231,
        agent_id="a9c3e7d1-2b4f-4e6a-9c8d-3f5a7b1e2c4d",
        agent_name="ada",
        user_id="11111111-2222-4333-8444-555566667777",
        org_id="00000000-0000-0000-0000-000000000100",
        correlation_id="0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
        endpoint="/ada/tools/read_file",
        method="POST",
        decision="allow",
        cost_estimate_usd=None,
        latency_ms=90,
        request_metadata={"policy_version": 36},
        entry_hash="globalhash",
        prev_hash="globalprev",
        entry_hash_org="orghash",
        prev_hash_org="orgprev",
        org_chain_seq=143,
        created_at=datetime.datetime(2026, 5, 4, 12, 0, 0, tzinfo=datetime.UTC),
    )
    base.update(overrides)
    return types.SimpleNamespace(**base)


class TestOcsfApiActivityMapping:
    def test_core_api_activity_fields(self):
        ev = audit_log_to_ocsf(_row())
        assert ev["class_uid"] == 6003  # API Activity
        assert ev["category_uid"] == 6  # Application Activity
        assert ev["activity_id"] == 1  # POST → Create
        assert ev["type_uid"] == 600301  # class_uid*100 + activity_id
        assert ev["metadata"]["profiles"] == ["ai_operation"]
        assert ev["metadata"]["version"] == OCSF_VERSION
        assert ev["metadata"]["correlation_uid"] == "0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d"

    def test_decision_maps_to_action_id(self):
        assert audit_log_to_ocsf(_row(decision="allow"))["action_id"] == 1
        assert audit_log_to_ocsf(_row(decision="allow"))["action"] == "Allowed"
        assert audit_log_to_ocsf(_row(decision="deny"))["action_id"] == 2
        assert audit_log_to_ocsf(_row(decision="error"))["action_id"] == 99

    def test_method_maps_to_activity_id(self):
        assert audit_log_to_ocsf(_row(method="GET"))["activity_id"] == 2
        assert audit_log_to_ocsf(_row(method="PATCH"))["activity_id"] == 3
        assert audit_log_to_ocsf(_row(method="DELETE"))["activity_id"] == 4
        # type_uid tracks activity_id
        assert audit_log_to_ocsf(_row(method="DELETE"))["type_uid"] == 600304

    def test_ai_agent_and_actor(self):
        ev = audit_log_to_ocsf(_row())
        assert ev["ai_agent"]["uid"] == "a9c3e7d1-2b4f-4e6a-9c8d-3f5a7b1e2c4d"
        assert ev["ai_agent"]["name"] == "ada"
        assert ev["actor"]["user"]["type_id"] == 1
        assert ev["http_request"]["http_method"] == "POST"
        assert ev["http_request"]["url"]["path"] == "/ada/tools/read_file"

    def test_attestation_prefers_org_chain(self):
        att = audit_log_to_ocsf(_row())["attestation"]
        assert att["entry_hash"] == "orghash"
        assert att["prev_entry_hash"] == "orgprev"
        assert att["chain_uid"] == "00000000-0000-0000-0000-000000000100"

    def test_attestation_falls_back_to_global_chain(self):
        att = audit_log_to_ocsf(_row(entry_hash_org=None, prev_hash_org=None))["attestation"]
        assert att["entry_hash"] == "globalhash"
        assert att["prev_entry_hash"] == "globalprev"
        assert "chain_uid" not in att

    def test_latency_maps_to_duration(self):
        ev = audit_log_to_ocsf(_row())
        assert ev["duration"] == 90  # OCSF base duration (ms), not unmapped
        assert "latency_ms" not in ev["unmapped"]

    def test_unmapped_carries_homeless_producer_facts(self):
        um = audit_log_to_ocsf(_row())["unmapped"]
        assert um["policy_version"] == 36
        assert um["org_chain_seq"] == 143

    def test_severity_elevated_on_deny(self):
        assert audit_log_to_ocsf(_row(decision="allow"))["severity_id"] == 1
        assert audit_log_to_ocsf(_row(decision="deny"))["severity_id"] == 3

    def test_long_form_decisions_map(self):
        # Some writers / older rows store "allowed"/"denied" (not "allow"/"deny").
        assert audit_log_to_ocsf(_row(decision="allowed"))["action_id"] == 1
        assert audit_log_to_ocsf(_row(decision="denied"))["action_id"] == 2
        assert audit_log_to_ocsf(_row(decision=" Allowed "))["action_id"] == 1  # strip + case

    def test_unknown_decision_is_not_elevated(self):
        ev = audit_log_to_ocsf(_row(decision="weird"))
        assert ev["action_id"] == 0
        assert ev["action"] == "Unknown"
        assert ev["severity_id"] == 1  # don't alarm on vocabulary we didn't classify
