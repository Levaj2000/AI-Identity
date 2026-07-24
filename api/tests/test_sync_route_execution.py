"""Regression tests for DB-bound route execution mode.

FastAPI runs plain ``def`` handlers and dependencies in its worker
threadpool. These routes use synchronous SQLAlchemy and, in a few cases,
synchronous email/network clients, so declaring them ``async def`` would
block the uvicorn event loop under slow DB or network calls.
"""

import inspect

from api.app import auth as auth_dependencies
from api.app.routers import (
    admin,
    approvals,
    auth,
    canned_responses,
    shadow,
    sla_escalation_cron,
    support_metrics,
    support_tickets,
    ticket_templates,
)
from api.app.routers import (
    attachments as attachment_routes,
)

SYNC_DB_BOUND_CALLABLES = [
    auth_dependencies.get_current_user,
    auth_dependencies.require_admin,
    auth.get_me,
    admin.get_platform_stats,
    admin.list_users,
    admin.create_user,
    admin.update_user_tier,
    admin.get_user_detail,
    admin.list_agents,
    admin.purge_revoked_agents,
    admin.purge_single_agent,
    admin.get_system_health,
    approvals.list_approvals,
    approvals.pending_count,
    approvals.get_approval,
    approvals.resolve_approval,
    attachment_routes.list_ticket_attachments,
    attachment_routes.delete_attachment,
    canned_responses.list_canned_responses,
    canned_responses.create_canned_response,
    canned_responses.get_canned_response,
    canned_responses.update_canned_response,
    canned_responses.delete_canned_response,
    shadow.shadow_stats,
    shadow.list_shadow_agents,
    shadow.shadow_agent_detail,
    shadow.block_shadow_agent,
    shadow.unblock_shadow_agent,
    shadow.dismiss_shadow_agent,
    shadow.undismiss_shadow_agent,
    sla_escalation_cron.escalate_overdue_tickets,
    support_metrics.get_support_metrics,
    support_tickets.create_ticket,
    support_tickets.list_tickets,
    support_tickets.get_ticket,
    support_tickets.update_ticket,
    support_tickets.add_comment,
    support_tickets.get_ticket_context,
    ticket_templates.list_ticket_templates,
    ticket_templates.create_ticket_template,
    ticket_templates.get_ticket_template,
    ticket_templates.update_ticket_template,
    ticket_templates.delete_ticket_template,
    ticket_templates.create_ticket_from_template,
]


def test_sync_db_bound_routes_run_in_fastapi_threadpool():
    offenders = [
        f"{fn.__module__}.{fn.__name__}"
        for fn in SYNC_DB_BOUND_CALLABLES
        if inspect.iscoroutinefunction(fn)
    ]

    assert offenders == []
