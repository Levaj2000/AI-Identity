"""SQLAlchemy database models for AI Identity."""

from common.models.agent import Agent, AgentStatus
from common.models.agent_assignment import AgentAssignment, AgentRole
from common.models.agent_key import AgentKey, KeyStatus, KeyType
from common.models.approval_request import ApprovalRequest, ApprovalStatus
from common.models.attestation import ForensicAttestation
from common.models.audit_log import AuditLog
from common.models.audit_outbox import AuditLogOutbox, OutboxStatus
from common.models.audit_sink import AuditLogSink, SinkKind
from common.models.base import Base, SessionLocal, engine, get_db
from common.models.blocked_agent import BlockedAgent
from common.models.canned_response import CannedResponse
from common.models.compliance import (
    ComplianceCheck,
    ComplianceFramework,
    ComplianceReport,
    ComplianceResult,
)
from common.models.compliance_export import ComplianceExport
from common.models.dismissed_shadow import DismissedShadowAgent
from common.models.org_membership import OrgMembership, OrgRole
from common.models.organization import Organization
from common.models.policy import Policy
from common.models.qa_run import QARun
from common.models.support_ticket import (
    SupportTicket,
    TicketCategory,
    TicketComment,
    TicketPriority,
    TicketStatus,
)
from common.models.ticket_template import TicketTemplate
from common.models.upstream_credential import (
    CredentialStatus,
    UpstreamCredential,
    UpstreamProvider,
)
from common.models.user import TIER_QUOTAS, User, UserTier

__all__ = [
    "Base",
    "SessionLocal",
    "engine",
    "get_db",
    "User",
    "Agent",
    "AgentStatus",
    "AgentKey",
    "KeyStatus",
    "KeyType",
    "Policy",
    "AuditLog",
    "ForensicAttestation",
    "AuditLogOutbox",
    "OutboxStatus",
    "AuditLogSink",
    "SinkKind",
    "UpstreamCredential",
    "CredentialStatus",
    "UpstreamProvider",
    "ComplianceFramework",
    "ComplianceCheck",
    "ComplianceReport",
    "ComplianceResult",
    "ComplianceExport",
    "UserTier",
    "TIER_QUOTAS",
    "QARun",
    "Organization",
    "OrgMembership",
    "OrgRole",
    "AgentAssignment",
    "AgentRole",
    "ApprovalRequest",
    "ApprovalStatus",
    "BlockedAgent",
    "DismissedShadowAgent",
    "SupportTicket",
    "TicketComment",
    "TicketPriority",
    "TicketStatus",
    "TicketCategory",
    "CannedResponse",
    "TicketTemplate",
]
