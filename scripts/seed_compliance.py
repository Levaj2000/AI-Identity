#!/usr/bin/env python3
"""Seed compliance frameworks and checks into the database.

Usage:
    python -m scripts.seed_compliance          # from repo root
    PYTHONPATH=. python scripts/seed_compliance.py
"""

import os
import sys

# Ensure repo root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models.base import Base, SessionLocal, engine
from common.models.compliance import ComplianceCheck, ComplianceFramework

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)


FRAMEWORKS = [
    {
        "name": "NIST AI Risk Management Framework",
        "version": "1.0",
        "description": "NIST AI RMF provides guidance for managing risks in the design, development, use, and evaluation of AI systems.",
        "category": "regulatory",
        "checks": [
            {
                "code": "NIST-GOV-01",
                "name": "Agent policy governance",
                "description": "All active agents must have at least one active policy defining allowed actions.",
                "severity": "high",
                "category": "governance",
                "check_type": "automated",
                "check_query": "all_agents_have_policies",
            },
            {
                "code": "NIST-GOV-02",
                "name": "Least privilege enforcement",
                "description": "Policies should not use unrestricted wildcard permissions — endpoints must be explicitly scoped.",
                "severity": "high",
                "category": "governance",
                "check_type": "automated",
                "check_query": "no_wildcard_only_policies",
            },
            {
                "code": "NIST-GOV-03",
                "name": "Agent capability declaration",
                "description": "Agents should have explicitly defined capabilities for risk categorization.",
                "severity": "medium",
                "category": "governance",
                "check_type": "automated",
                "check_query": "agent_capabilities_defined",
            },
            {
                "code": "NIST-MAP-01",
                "name": "Audit trail integrity",
                "description": "The HMAC audit chain must be intact — no tampered or missing entries.",
                "severity": "critical",
                "category": "accountability",
                "check_type": "automated",
                "check_query": "audit_chain_integrity",
            },
            {
                "code": "NIST-MAP-02",
                "name": "Audit log coverage",
                "description": "Active agents should have audit log entries demonstrating monitored operation.",
                "severity": "medium",
                "category": "accountability",
                "check_type": "automated",
                "check_query": "audit_entries_exist",
            },
            {
                "code": "NIST-MEA-01",
                "name": "Credential rotation cadence",
                "description": "API keys should be rotated within 90 days per security best practices.",
                "severity": "medium",
                "category": "security",
                "check_type": "automated",
                "check_query": "key_rotation_90_days",
            },
            {
                "code": "NIST-MAN-01",
                "name": "Revoked agent key cleanup",
                "description": "Revoked agents must not have any active keys that could be used for access.",
                "severity": "critical",
                "category": "security",
                "check_type": "automated",
                "check_query": "no_revoked_agents_active_keys",
            },
        ],
    },
    {
        "name": "EU AI Act",
        "version": "2024",
        "description": "The European Union AI Act establishes rules for AI systems based on risk classification, with requirements for transparency, accountability, and human oversight.",
        "category": "regulatory",
        "checks": [
            {
                "code": "EUAI-TRANS-01",
                "name": "Agent transparency — description required",
                "description": "All AI agents must have human-readable descriptions explaining their purpose and function (Article 13).",
                "severity": "high",
                "category": "transparency",
                "check_type": "automated",
                "check_query": "agent_has_description",
            },
            {
                "code": "EUAI-TRANS-02",
                "name": "Capability disclosure",
                "description": "AI systems must disclose their capabilities to users and affected parties (Article 13.3).",
                "severity": "high",
                "category": "transparency",
                "check_type": "automated",
                "check_query": "agent_capabilities_defined",
            },
            {
                "code": "EUAI-ACC-01",
                "name": "Decision audit trail",
                "description": "High-risk AI systems must maintain logs of decisions for post-hoc review (Article 12).",
                "severity": "critical",
                "category": "accountability",
                "check_type": "automated",
                "check_query": "audit_entries_exist",
            },
            {
                "code": "EUAI-ACC-02",
                "name": "Audit integrity verification",
                "description": "Audit logs must be tamper-evident with cryptographic integrity (Article 12.4).",
                "severity": "critical",
                "category": "accountability",
                "check_type": "automated",
                "check_query": "audit_chain_integrity",
            },
            {
                "code": "EUAI-GOV-01",
                "name": "Access control governance",
                "description": "AI systems must implement appropriate access controls with separation of duties (Article 9).",
                "severity": "high",
                "category": "governance",
                "check_type": "automated",
                "check_query": "key_type_separation",
            },
            {
                "code": "EUAI-SEC-01",
                "name": "Credential protection",
                "description": "Sensitive data including API credentials must be encrypted at rest (Article 15).",
                "severity": "critical",
                "category": "security",
                "check_type": "automated",
                "check_query": "credentials_encrypted",
            },
        ],
    },
    {
        "name": "SOC 2 — AI Agent Controls",
        "version": "2024",
        "description": "SOC 2 Trust Service Criteria mapped to AI agent management — security, availability, processing integrity, confidentiality, and privacy.",
        "category": "industry",
        "checks": [
            {
                "code": "SOC2-CC6.1",
                "name": "Logical access controls",
                "description": "The entity implements logical access security over information assets (agent policies).",
                "severity": "high",
                "category": "security",
                "check_type": "automated",
                "check_query": "all_agents_have_policies",
            },
            {
                "code": "SOC2-CC6.3",
                "name": "Least privilege access",
                "description": "Access is restricted to authorized users and follows the principle of least privilege.",
                "severity": "high",
                "category": "security",
                "check_type": "automated",
                "check_query": "no_wildcard_only_policies",
            },
            {
                "code": "SOC2-CC6.6",
                "name": "Key management lifecycle",
                "description": "Cryptographic keys are managed through their lifecycle including rotation and revocation.",
                "severity": "high",
                "category": "security",
                "check_type": "automated",
                "check_query": "key_rotation_90_days",
            },
            {
                "code": "SOC2-CC6.7",
                "name": "Key revocation enforcement",
                "description": "Revoked entities must not retain any active access credentials.",
                "severity": "critical",
                "category": "security",
                "check_type": "automated",
                "check_query": "no_revoked_agents_active_keys",
            },
            {
                "code": "SOC2-CC7.2",
                "name": "Security event monitoring",
                "description": "Security events are logged and monitored with tamper-evident integrity.",
                "severity": "critical",
                "category": "accountability",
                "check_type": "automated",
                "check_query": "audit_chain_integrity",
            },
            {
                "code": "SOC2-CC8.1",
                "name": "Credential encryption at rest",
                "description": "Sensitive credentials are encrypted when stored to prevent unauthorized disclosure.",
                "severity": "critical",
                "category": "security",
                "check_type": "automated",
                "check_query": "credentials_encrypted",
            },
            {
                "code": "SOC2-CC9.1",
                "name": "Credential identification",
                "description": "Stored credentials are identifiable via prefixes without exposing sensitive data.",
                "severity": "medium",
                "category": "security",
                "check_type": "automated",
                "check_query": "credentials_have_prefixes",
            },
        ],
    },
    {
        "name": "AI Identity Best Practices",
        "version": "1.0",
        "description": "Internal best practices for AI agent identity management — opinionated checks based on production learnings.",
        "category": "internal",
        "checks": [
            {
                "code": "AIID-SEC-01",
                "name": "All agents have active policies",
                "description": "Every active agent must be governed by at least one active policy.",
                "severity": "high",
                "category": "security",
                "check_type": "automated",
                "check_query": "all_agents_have_policies",
            },
            {
                "code": "AIID-SEC-02",
                "name": "No overly permissive policies",
                "description": "Policies should not grant unrestricted access via wildcard-only rules.",
                "severity": "high",
                "category": "security",
                "check_type": "automated",
                "check_query": "no_wildcard_only_policies",
            },
            {
                "code": "AIID-SEC-03",
                "name": "Credentials encrypted at rest",
                "description": "All upstream API credentials must be Fernet-encrypted in the database.",
                "severity": "critical",
                "category": "security",
                "check_type": "automated",
                "check_query": "credentials_encrypted",
            },
            {
                "code": "AIID-SEC-04",
                "name": "Key rotation hygiene",
                "description": "API keys should be rotated at least every 90 days.",
                "severity": "medium",
                "category": "security",
                "check_type": "automated",
                "check_query": "key_rotation_90_days",
            },
            {
                "code": "AIID-SEC-05",
                "name": "Key type separation",
                "description": "Agents should use either runtime or admin keys, not both simultaneously.",
                "severity": "medium",
                "category": "security",
                "check_type": "automated",
                "check_query": "key_type_separation",
            },
            {
                "code": "AIID-SEC-06",
                "name": "No orphaned active keys",
                "description": "Revoked agents must not have active keys.",
                "severity": "critical",
                "category": "security",
                "check_type": "automated",
                "check_query": "no_revoked_agents_active_keys",
            },
            {
                "code": "AIID-AUD-01",
                "name": "Audit chain integrity",
                "description": "The HMAC audit chain must pass integrity verification.",
                "severity": "critical",
                "category": "accountability",
                "check_type": "automated",
                "check_query": "audit_chain_integrity",
            },
            {
                "code": "AIID-AUD-02",
                "name": "Audit coverage for active agents",
                "description": "All active agents should have at least one audit trail entry.",
                "severity": "medium",
                "category": "accountability",
                "check_type": "automated",
                "check_query": "audit_entries_exist",
            },
            {
                "code": "AIID-GOV-01",
                "name": "Agent descriptions for transparency",
                "description": "Every agent should have a human-readable description.",
                "severity": "low",
                "category": "transparency",
                "check_type": "automated",
                "check_query": "agent_has_description",
            },
            {
                "code": "AIID-GOV-02",
                "name": "Capabilities explicitly declared",
                "description": "Agents should declare their capabilities for governance and risk management.",
                "severity": "low",
                "category": "transparency",
                "check_type": "automated",
                "check_query": "agent_capabilities_defined",
            },
        ],
    },
]


def seed():
    """Seed compliance frameworks and checks (idempotent — skips existing)."""
    db = SessionLocal()

    try:
        for fw_data in FRAMEWORKS:
            # Check if framework already exists
            existing = (
                db.query(ComplianceFramework)
                .filter(ComplianceFramework.name == fw_data["name"])
                .first()
            )
            if existing:
                print(f"  Skipping (exists): {fw_data['name']}")
                continue

            framework = ComplianceFramework(
                name=fw_data["name"],
                version=fw_data["version"],
                description=fw_data["description"],
                category=fw_data["category"],
            )
            db.add(framework)
            db.flush()  # Get the ID

            for check_data in fw_data["checks"]:
                check = ComplianceCheck(
                    framework_id=framework.id,
                    code=check_data["code"],
                    name=check_data["name"],
                    description=check_data["description"],
                    severity=check_data["severity"],
                    category=check_data["category"],
                    check_type=check_data["check_type"],
                    check_query=check_data.get("check_query"),
                )
                db.add(check)

            db.commit()
            print(f"  Seeded: {fw_data['name']} ({len(fw_data['checks'])} checks)")

        print("\nDone!")
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding compliance frameworks...")
    seed()
