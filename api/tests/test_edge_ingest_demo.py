"""The demo assets feed the real ingest endpoint end-to-end.

Loads scripts/demo_edge_ingest.py and drives its four acts through the
actual API: the signed $100-agent story verifies, the replay dedupes,
the tampered record quarantines, and the lost-epoch record verifies with
the gap surfaced. If the demo script and the verifier ever drift apart,
this is the test that says so before a live demo does.
"""

import importlib.util
import pathlib

import pytest

from common.models import EdgeAuditEvent, OrgMembership

_SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "demo_edge_ingest.py"
_spec = importlib.util.spec_from_file_location("demo_edge_ingest", _SCRIPT)
demo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(demo)


@pytest.fixture
def demo_edge(client, db_session, test_user, auth_headers):
    """An edge registered with the demo script's chain identity and key."""
    db_session.add(OrgMembership(org_id=test_user.org_id, user_id=test_user.id, role="owner"))
    db_session.commit()
    resp = client.post(
        "/api/v1/edges",
        headers=auth_headers,
        json={
            "name": "Edge demo — $100 Agent",
            "chain_uid": demo.CHAIN_UID,
            "verify_key_pem": demo.demo_public_key_pem(),
            "key_id": "edge-demo-key-1",
        },
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['ingest_key']}"}


def test_demo_story_plays_all_four_acts(client, db_session, demo_edge):
    story = demo.build_story()

    # Act 1 — the $100 agent: three draws land, the fourth is denied
    act1 = client.post("/api/v1/audit/ingest", headers=demo_edge, content=demo.ndjson(story))
    assert act1.status_code == 202, act1.text
    data = act1.json()
    assert data["verified"] == 4 and data["quarantined"] == 0 and data["anomalies"] == 0
    assert [r["chain_position"] for r in data["results"]] == [1, 2, 3, 4]
    denied = db_session.query(EdgeAuditEvent).filter_by(metadata_uid="draw-004").one()
    assert denied.event["action"] == "Denied"
    assert denied.event["status_code"] == "mandate_exceeded"
    # The draw-receipt join key rides inside the verified bytes
    assert denied.event["unmapped"]["cmf.request.request_id"] == "corr-d4e55b37"

    # Act 2 — replay: at-least-once, nothing re-stored
    act2 = client.post("/api/v1/audit/ingest", headers=demo_edge, content=demo.ndjson(story)).json()
    assert act2["duplicates"] == 4 and act2["verified"] == 0
    assert db_session.query(EdgeAuditEvent).count() == 4

    # Act 3 — a record edited after signing: quarantined, stored verbatim
    tampered = demo.build_tampered(story)
    act3 = client.post(
        "/api/v1/audit/ingest", headers=demo_edge, content=demo.ndjson([tampered])
    ).json()
    assert act3["quarantined"] == 1
    assert "fingerprint mismatch" in act3["results"][0]["reason"]
    row = db_session.query(EdgeAuditEvent).filter_by(metadata_uid="draw-evil").one()
    assert row.verification_status == "quarantined"

    # Act 4 — after a lost epoch: verified WITH the gap surfaced, chain re-anchored
    gap = demo.build_gap_record(story)
    act4 = client.post("/api/v1/audit/ingest", headers=demo_edge, content=demo.ndjson([gap])).json()
    assert act4["verified"] == 1 and act4["anomalies"] == 1
    result = act4["results"][0]
    assert result["status"] == "verified" and result["chain_position"] == 5
    assert "stream_seq gap" in result["anomalies"]
