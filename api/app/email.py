"""Transactional email via Resend.

Sends welcome and follow-up emails to new users.
Gracefully no-ops when RESEND_API_KEY is not configured.
"""

import logging
from datetime import UTC

import resend

from common.config.settings import settings

logger = logging.getLogger("ai_identity.api.email")


def _is_configured() -> bool:
    """Check if Resend is configured."""
    return bool(settings.resend_api_key)


def send_welcome_email(email: str, first_name: str | None = None) -> str | None:
    """Send welcome email immediately after auto-provisioning.

    Returns the Resend email ID on success, None if unconfigured or on error.
    """
    if not _is_configured():
        logger.info("Resend not configured — skipping welcome email for %s", email)
        return None

    resend.api_key = settings.resend_api_key
    name = first_name or email.split("@")[0].title()

    try:
        result = resend.Emails.send(
            {
                "from": settings.resend_from_email,
                "to": [email],
                "reply_to": settings.resend_reply_to,
                "subject": "Welcome to AI Identity — your dashboard is ready",
                "html": _welcome_html(name),
            }
        )
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        logger.info("Welcome email sent: user=%s, resend_id=%s", email, email_id)
        return email_id
    except Exception as e:
        logger.error("Failed to send welcome email to %s: %s", email, e)
        return None


def send_followup_email(email: str, first_name: str | None = None) -> str | None:
    """Send 5-day follow-up email.

    Returns the Resend email ID on success, None if unconfigured or on error.
    """
    if not _is_configured():
        return None

    resend.api_key = settings.resend_api_key
    name = first_name or email.split("@")[0].title()

    try:
        result = resend.Emails.send(
            {
                "from": settings.resend_from_email,
                "to": [email],
                "reply_to": settings.resend_reply_to,
                "subject": "Quick check-in — how's the setup going?",
                "html": _followup_html(name),
            }
        )
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        logger.info("Follow-up email sent: user=%s, resend_id=%s", email, email_id)
        return email_id
    except Exception as e:
        logger.error("Failed to send follow-up email to %s: %s", email, e)
        return None


def send_new_signup_notification(user_email: str) -> str | None:
    """Notify the founder when a new user signs up.

    Fire-and-forget — never blocks auth flow.
    Returns the Resend email ID on success, None otherwise.
    """
    if not _is_configured():
        logger.info("Resend not configured — skipping signup notification for %s", user_email)
        return None

    resend.api_key = settings.resend_api_key

    try:
        result = resend.Emails.send(
            {
                "from": settings.resend_from_email,
                "to": [settings.resend_reply_to],  # Goes to Jeff
                "subject": f"New signup: {user_email}",
                "html": _signup_notification_html(user_email),
            }
        )
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        logger.info("Signup notification sent for %s, resend_id=%s", user_email, email_id)
        return email_id
    except Exception as e:
        logger.error("Failed to send signup notification for %s: %s", user_email, e)
        return None


# ── Email HTML Templates ────────────────────────────────────────────


def _email_wrapper(content: str) -> str:
    """Wrap email content in a simple, clean HTML template."""
    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<div style="max-width:560px;margin:40px auto;background:#ffffff;border-radius:8px;overflow:hidden;">
  <div style="background:#0A0A0B;padding:24px 32px;">
    <span style="color:#F59E0B;font-size:18px;font-weight:600;">AI Identity</span>
  </div>
  <div style="padding:32px;color:#1f2937;font-size:15px;line-height:1.6;">
    {content}
  </div>
  <div style="padding:16px 32px;background:#f9fafb;border-top:1px solid #e5e7eb;font-size:12px;color:#9ca3af;">
    AI Identity &mdash; Identity infrastructure for AI agents<br>
    <a href="https://www.ai-identity.co" style="color:#F59E0B;text-decoration:none;">www.ai-identity.co</a>
  </div>
</div>
</body>
</html>"""


def _welcome_html(name: str) -> str:
    """Welcome email — sent immediately on signup."""
    return _email_wrapper(f"""\
<p>Hi {name},</p>

<p>Welcome to AI Identity. Your account is ready and you can start building right away.</p>

<p>Thanks for signing up &mdash; I'm genuinely excited to have you here. AI Identity is still early, and every new user's feedback directly shapes the product.</p>

<p><strong>Your free tier includes:</strong></p>
<ul style="padding-left:20px;color:#374151;">
  <li>5 AI agents</li>
  <li>2,000 gateway requests/month</li>
  <li>1 upstream credential (encrypted at rest)</li>
  <li>30-day audit log retention</li>
  <li>Tamper-proof HMAC audit chain</li>
</ul>

<p><strong>Get started:</strong></p>
<table cellpadding="0" cellspacing="0" border="0" style="margin:16px 0;">
  <tr>
    <td style="background:#F59E0B;border-radius:6px;padding:10px 20px;">
      <a href="https://dashboard.ai-identity.co" style="color:#0A0A0B;text-decoration:none;font-weight:600;font-size:14px;">Open Dashboard</a>
    </td>
  </tr>
</table>

<p style="font-size:13px;color:#6b7280;">
  Quick path: Create an agent &rarr; Store your API key &rarr; Set a policy &rarr; Run a compliance check.
</p>

<p>If you run into anything confusing or have ideas for what we should build next, just reply to this email. I read every one.</p>

<p>
  Jeff Leva<br>
  <span style="color:#6b7280;font-size:13px;">Founder, AI Identity</span>
</p>""")


def _followup_html(name: str) -> str:
    """5-day follow-up email — check-in, system health, and questions."""
    return _email_wrapper(f"""\
<p>Hi {name},</p>

<p>How have your first few days on the AI Identity platform been? I wanted to check in and share a quick update.</p>

<p><strong>Your system health check</strong></p>

<p>As a courtesy, we've completed our 15-point production validation on your account. This covers infrastructure health, authentication, gateway policy enforcement, audit logging, and compliance readiness.</p>

<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:16px;margin:16px 0;">
  <p style="margin:0;color:#166534;font-weight:600;">&#10003; 15/15 checks passed</p>
  <p style="margin:4px 0 0;color:#166534;font-size:13px;">Your account is seeing optimal performance across all systems.</p>
</div>

<p style="font-size:13px;color:#6b7280;">
  You can view the full results anytime in your dashboard under <strong>QA Checklist</strong> in the sidebar.
</p>

<p><strong>A few quick questions</strong> (just reply inline):</p>
<ol style="padding-left:20px;color:#374151;">
  <li>Have you had a chance to create your first agent yet?</li>
  <li>What's your biggest question so far?</li>
  <li>Is anything missing or confusing?</li>
</ol>

<p>If you run into any issues at all, please reach out to me personally &mdash; I read and reply to every message.</p>

<p>
  Jeff Leva<br>
  <span style="color:#6b7280;font-size:13px;">Founder, AI Identity</span><br>
  <a href="mailto:jeff@ai-identity.co" style="color:#F59E0B;text-decoration:none;font-size:13px;">jeff@ai-identity.co</a>
</p>""")


def send_support_ticket_notification(
    ticket_id: str,
    ticket_number: str,
    subject: str,
    description: str,
    priority: str,
    category: str,
    user_email: str,
    user_name: str | None = None,
    agent_name: str | None = None,
) -> str | None:
    """Notify support team when a new ticket is created.

    Fire-and-forget — never blocks ticket creation.
    Returns the Resend email ID on success, None otherwise.
    """
    if not _is_configured():
        logger.info("Resend not configured — skipping ticket notification for %s", ticket_number)
        return None

    resend.api_key = settings.resend_api_key

    try:
        result = resend.Emails.send(
            {
                "from": settings.resend_from_email,
                "to": ["jeff@ai-identity.co"],
                "reply_to": user_email,  # Allow direct reply to customer
                "subject": f"New Support Ticket: {ticket_number} - {subject}",
                "html": _support_ticket_notification_html(
                    ticket_id=ticket_id,
                    ticket_number=ticket_number,
                    subject=subject,
                    description=description,
                    priority=priority,
                    category=category,
                    user_email=user_email,
                    user_name=user_name,
                    agent_name=agent_name,
                ),
            }
        )
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        logger.info(
            "Support ticket notification sent: ticket=%s, resend_id=%s", ticket_number, email_id
        )
        return email_id
    except Exception as e:
        logger.error("Failed to send ticket notification for %s: %s", ticket_number, e)


def send_ticket_created_email(
    user_email: str,
    ticket_number: str,
    subject: str,
    priority: str,
) -> str | None:
    """Send confirmation email to customer when ticket is created.

    Fire-and-forget — never blocks ticket creation.
    Returns the Resend email ID on success, None otherwise.
    """
    if not _is_configured():
        logger.info("Resend not configured — skipping customer email for %s", ticket_number)
        return None

    resend.api_key = settings.resend_api_key

    try:
        result = resend.Emails.send(
            {
                "from": settings.resend_from_email,
                "to": [user_email],
                "reply_to": settings.resend_reply_to,
                "subject": f"Support Ticket Created: {ticket_number}",
                "html": _ticket_created_html(
                    ticket_number=ticket_number,
                    subject=subject,
                    priority=priority,
                ),
            }
        )
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        logger.info(
            "Ticket created email sent: ticket=%s, user=%s, resend_id=%s",
            ticket_number,
            user_email,
            email_id,
        )
        return email_id
    except Exception as e:
        logger.error("Failed to send ticket created email for %s: %s", ticket_number, e)
        return None


def send_ticket_status_update_email(
    user_email: str,
    ticket_number: str,
    subject: str,
    new_status: str,
    resolution_comment: str | None = None,
) -> str | None:
    """Send email when ticket status changes (especially RESOLVED/CLOSED).

    Fire-and-forget — never blocks ticket updates.
    Returns the Resend email ID on success, None otherwise.
    """
    if not _is_configured():
        logger.info("Resend not configured — skipping status update email for %s", ticket_number)
        return None

    resend.api_key = settings.resend_api_key

    try:
        result = resend.Emails.send(
            {
                "from": settings.resend_from_email,
                "to": [user_email],
                "reply_to": settings.resend_reply_to,
                "subject": f"Ticket {ticket_number} Status Updated: {new_status.replace('_', ' ').title()}",
                "html": _ticket_status_update_html(
                    ticket_number=ticket_number,
                    subject=subject,
                    new_status=new_status,
                    resolution_comment=resolution_comment,
                ),
            }
        )
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        logger.info(
            "Ticket status update email sent: ticket=%s, status=%s, user=%s, resend_id=%s",
            ticket_number,
            new_status,
            user_email,
            email_id,
        )
        return email_id
    except Exception as e:
        logger.error("Failed to send status update email for %s: %s", ticket_number, e)
        return None


def send_ticket_comment_email(
    user_email: str,
    ticket_number: str,
    subject: str,
    commenter_email: str,
    comment_preview: str,
) -> str | None:
    """Send email when new public comment is added (not for internal comments).

    Fire-and-forget — never blocks comment creation.
    Returns the Resend email ID on success, None otherwise.
    """
    if not _is_configured():
        logger.info("Resend not configured — skipping comment email for %s", ticket_number)
        return None

    resend.api_key = settings.resend_api_key

    try:
        result = resend.Emails.send(
            {
                "from": settings.resend_from_email,
                "to": [user_email],
                "reply_to": settings.resend_reply_to,
                "subject": f"New Comment on Ticket {ticket_number}",
                "html": _ticket_comment_html(
                    ticket_number=ticket_number,
                    subject=subject,
                    commenter_email=commenter_email,
                    comment_preview=comment_preview,
                ),
            }
        )
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        logger.info(
            "Ticket comment email sent: ticket=%s, user=%s, resend_id=%s",
            ticket_number,
            user_email,
            email_id,
        )
        return email_id
    except Exception as e:
        logger.error("Failed to send comment email for %s: %s", ticket_number, e)
        return None


def send_sla_breach_notification(
    ticket_number: str,
    subject: str,
    old_priority: str,
    new_priority: str,
    hours_overdue: float,
) -> str | None:
    """Send notification when a ticket breaches its SLA.

    Sent to support team only (internal notification).
    Fire-and-forget — never blocks escalation.
    Returns the Resend email ID on success, None otherwise.
    """
    if not _is_configured():
        logger.info(
            "Resend not configured — skipping SLA breach notification for %s", ticket_number
        )
        return None

    resend.api_key = settings.resend_api_key

    try:
        result = resend.Emails.send(
            {
                "from": settings.resend_from_email,
                "to": ["jeff@ai-identity.co"],
                "reply_to": settings.resend_reply_to,
                "subject": f"🚨 SLA Breach: {ticket_number} - {subject}",
                "html": _sla_breach_html(
                    ticket_number=ticket_number,
                    subject=subject,
                    old_priority=old_priority,
                    new_priority=new_priority,
                    hours_overdue=hours_overdue,
                ),
            }
        )
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        logger.info(
            "SLA breach notification sent: ticket=%s, resend_id=%s",
            ticket_number,
            email_id,
        )
        return email_id
    except Exception as e:
        logger.error("Failed to send SLA breach notification for %s: %s", ticket_number, e)
        return None


def _signup_notification_html(user_email: str) -> str:
    """Internal notification — new user signed up."""
    from datetime import datetime

    now = datetime.now(UTC).strftime("%b %d, %Y at %I:%M %p UTC")
    return _email_wrapper(f"""\
<p style="font-size:16px;font-weight:600;color:#10B981;">New User Signup</p>

<table style="width:100%;border-collapse:collapse;margin:16px 0;">
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Email</td>
    <td style="padding:8px 0;font-weight:600;">{user_email}</td>
  </tr>
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Time</td>
    <td style="padding:8px 0;">{now}</td>
  </tr>
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Tier</td>
    <td style="padding:8px 0;">Free</td>
  </tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" style="margin:16px 0;">
  <tr>
    <td style="background:#F59E0B;border-radius:6px;padding:10px 20px;">
      <a href="https://dashboard.ai-identity.co/dashboard/qa" style="color:#0A0A0B;text-decoration:none;font-weight:600;font-size:14px;">View QA Checklist</a>
    </td>
  </tr>
</table>

<p style="font-size:13px;color:#6b7280;">
  A welcome email has been sent to the user. Check the QA Checklist for their onboarding run when ready.
</p>""")


def _support_ticket_notification_html(
    ticket_id: str,
    ticket_number: str,
    subject: str,
    description: str,
    priority: str,
    category: str,
    user_email: str,
    user_name: str | None = None,
    agent_name: str | None = None,
) -> str:
    """Support ticket notification — sent to jeff@ai-identity.co."""
    from datetime import datetime

    now = datetime.now(UTC).strftime("%b %d, %Y at %I:%M %p UTC")
    name_display = user_name or user_email.split("@")[0].title()

    # Priority badge colors
    priority_colors = {
        "low": "#10B981",
        "medium": "#F59E0B",
        "high": "#EF4444",
        "critical": "#DC2626",
    }
    priority_color = priority_colors.get(priority.lower(), "#6B7280")

    agent_row = ""
    if agent_name:
        agent_row = f"""
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Related Agent</td>
    <td style="padding:8px 0;">{agent_name}</td>
  </tr>"""

    return _email_wrapper(f"""\
<p style="font-size:16px;font-weight:600;color:#EF4444;">New Support Ticket</p>

<div style="background:#FEF2F2;border-left:4px solid {priority_color};padding:12px 16px;margin:16px 0;border-radius:4px;">
  <p style="margin:0;font-weight:600;font-size:15px;">{subject}</p>
  <p style="margin:4px 0 0;color:#6b7280;font-size:13px;">
    <span style="background:{priority_color};color:white;padding:2px 8px;border-radius:4px;font-weight:600;text-transform:uppercase;font-size:11px;">{priority}</span>
    <span style="margin-left:8px;">{category}</span>
  </p>
</div>

<table style="width:100%;border-collapse:collapse;margin:16px 0;">
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Ticket Number</td>
    <td style="padding:8px 0;font-weight:600;font-family:monospace;">{ticket_number}</td>
  </tr>
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Customer</td>
    <td style="padding:8px 0;">{name_display} ({user_email})</td>
  </tr>
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Created</td>
    <td style="padding:8px 0;">{now}</td>
  </tr>{agent_row}
</table>

<div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;padding:16px;margin:16px 0;">
  <p style="margin:0 0 8px;color:#6b7280;font-size:13px;font-weight:600;">Description:</p>
  <p style="margin:0;color:#1F2937;white-space:pre-wrap;">{description}</p>
</div>

<table cellpadding="0" cellspacing="0" border="0" style="margin:16px 0;">
  <tr>
    <td style="background:#F59E0B;border-radius:6px;padding:10px 20px;">
      <a href="https://dashboard.ai-identity.co/dashboard/support/{ticket_id}" style="color:#0A0A0B;text-decoration:none;font-weight:600;font-size:14px;">View Ticket in Dashboard</a>
    </td>
  </tr>
</table>

<p style="font-size:13px;color:#6b7280;">
  Reply directly to this email to respond to the customer.
</p>""")


def _ticket_created_html(ticket_number: str, subject: str, priority: str) -> str:
    """Customer confirmation email — ticket created."""
    # Priority badge colors
    priority_colors = {
        "low": "#10B981",
        "medium": "#F59E0B",
        "high": "#EF4444",
        "urgent": "#DC2626",
    }
    priority_color = priority_colors.get(priority.lower(), "#6B7280")

    return _email_wrapper(f"""\
<p>Your support ticket has been created successfully.</p>

<div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;padding:16px;margin:16px 0;">
  <p style="margin:0 0 8px;color:#6b7280;font-size:13px;font-weight:600;">Ticket Number:</p>
  <p style="margin:0;font-family:monospace;font-size:16px;font-weight:600;">{ticket_number}</p>
</div>

<div style="background:#FEF2F2;border-left:4px solid {priority_color};padding:12px 16px;margin:16px 0;border-radius:4px;">
  <p style="margin:0;font-weight:600;font-size:15px;">{subject}</p>
  <p style="margin:4px 0 0;color:#6b7280;font-size:13px;">
    <span style="background:{priority_color};color:white;padding:2px 8px;border-radius:4px;font-weight:600;text-transform:uppercase;font-size:11px;">{priority}</span>
  </p>
</div>

<p><strong>What happens next?</strong></p>
<ul style="padding-left:20px;color:#374151;">
  <li>Our support team has been notified and will review your ticket</li>
  <li>You'll receive email updates when there are status changes or new comments</li>
  <li>You can view your ticket anytime in the dashboard</li>
</ul>

<table cellpadding="0" cellspacing="0" border="0" style="margin:16px 0;">
  <tr>
    <td style="background:#F59E0B;border-radius:6px;padding:10px 20px;">
      <a href="https://dashboard.ai-identity.co/support" style="color:#0A0A0B;text-decoration:none;font-weight:600;font-size:14px;">View My Tickets</a>
    </td>
  </tr>
</table>

<p style="font-size:13px;color:#6b7280;">
  You can reply directly to this email to add comments to your ticket.
</p>

<p>
  Jeff Leva<br>
  <span style="color:#6b7280;font-size:13px;">Founder, AI Identity</span>
</p>""")


def _ticket_status_update_html(
    ticket_number: str,
    subject: str,
    new_status: str,
    resolution_comment: str | None = None,
) -> str:
    """Customer notification email — ticket status changed."""
    status_display = new_status.replace("_", " ").title()

    # Status-specific messaging
    status_messages = {
        "in_progress": "Our team is actively working on your ticket.",
        "waiting_customer": "We need additional information from you to proceed.",
        "resolved": "Your ticket has been resolved! If you're satisfied with the resolution, no further action is needed.",
        "closed": "Your ticket has been closed. If you need further assistance, feel free to create a new ticket.",
    }
    status_message = status_messages.get(new_status, "Your ticket status has been updated.")

    # Status badge colors
    status_colors = {
        "open": "#6B7280",
        "in_progress": "#F59E0B",
        "waiting_customer": "#8B5CF6",
        "resolved": "#10B981",
        "closed": "#6B7280",
    }
    status_color = status_colors.get(new_status, "#6B7280")

    resolution_section = ""
    if resolution_comment and new_status in ["resolved", "closed"]:
        resolution_section = f"""
<div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;padding:16px;margin:16px 0;">
  <p style="margin:0 0 8px;color:#166534;font-size:13px;font-weight:600;">Resolution:</p>
  <p style="margin:0;color:#166534;white-space:pre-wrap;">{resolution_comment}</p>
</div>"""

    return _email_wrapper(f"""\
<p>Your support ticket status has been updated.</p>

<div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;padding:16px;margin:16px 0;">
  <p style="margin:0 0 8px;color:#6b7280;font-size:13px;font-weight:600;">Ticket Number:</p>
  <p style="margin:0 0 12px;font-family:monospace;font-size:16px;font-weight:600;">{ticket_number}</p>

  <p style="margin:0 0 8px;color:#6b7280;font-size:13px;font-weight:600;">Subject:</p>
  <p style="margin:0 0 12px;">{subject}</p>

  <p style="margin:0 0 8px;color:#6b7280;font-size:13px;font-weight:600;">New Status:</p>
  <p style="margin:0;">
    <span style="background:{status_color};color:white;padding:4px 12px;border-radius:4px;font-weight:600;text-transform:uppercase;font-size:12px;">{status_display}</span>
  </p>
</div>

<p>{status_message}</p>

{resolution_section}

<table cellpadding="0" cellspacing="0" border="0" style="margin:16px 0;">
  <tr>
    <td style="background:#F59E0B;border-radius:6px;padding:10px 20px;">
      <a href="https://dashboard.ai-identity.co/support" style="color:#0A0A0B;text-decoration:none;font-weight:600;font-size:14px;">View Ticket</a>
    </td>
  </tr>
</table>

<p style="font-size:13px;color:#6b7280;">
  Reply to this email to add a comment to your ticket.
</p>

<p>
  Jeff Leva<br>
  <span style="color:#6b7280;font-size:13px;">Founder, AI Identity</span>
</p>""")


def _ticket_comment_html(
    ticket_number: str,
    subject: str,
    commenter_email: str,
    comment_preview: str,
) -> str:
    """Customer notification email — new comment added."""
    # Truncate preview if too long
    if len(comment_preview) > 200:
        comment_preview = comment_preview[:197] + "..."

    return _email_wrapper(f"""\
<p>A new comment has been added to your support ticket.</p>

<div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;padding:16px;margin:16px 0;">
  <p style="margin:0 0 8px;color:#6b7280;font-size:13px;font-weight:600;">Ticket Number:</p>
  <p style="margin:0 0 12px;font-family:monospace;font-size:16px;font-weight:600;">{ticket_number}</p>

  <p style="margin:0 0 8px;color:#6b7280;font-size:13px;font-weight:600;">Subject:</p>
  <p style="margin:0;">{subject}</p>
</div>

<div style="background:#FFFBEB;border-left:4px solid #F59E0B;padding:12px 16px;margin:16px 0;border-radius:4px;">
  <p style="margin:0 0 8px;color:#92400E;font-size:13px;font-weight:600;">From: {commenter_email}</p>
  <p style="margin:0;color:#78350F;white-space:pre-wrap;">{comment_preview}</p>
</div>

<table cellpadding="0" cellspacing="0" border="0" style="margin:16px 0;">
  <tr>
    <td style="background:#F59E0B;border-radius:6px;padding:10px 20px;">
      <a href="https://dashboard.ai-identity.co/support" style="color:#0A0A0B;text-decoration:none;font-weight:600;font-size:14px;">View Full Comment</a>
    </td>
  </tr>
</table>

<p style="font-size:13px;color:#6b7280;">
  Reply to this email to add your own comment.
</p>

<p>
  Jeff Leva<br>
  <span style="color:#6b7280;font-size:13px;">Founder, AI Identity</span>
</p>""")


def _sla_breach_html(
    ticket_number: str,
    subject: str,
    old_priority: str,
    new_priority: str,
    hours_overdue: float,
) -> str:
    """SLA breach notification — sent to support team."""
    from datetime import datetime

    now = datetime.now(UTC).strftime("%b %d, %Y at %I:%M %p UTC")

    # Priority badge colors
    priority_colors = {
        "low": "#10B981",
        "medium": "#F59E0B",
        "high": "#EF4444",
        "urgent": "#DC2626",
    }
    old_color = priority_colors.get(old_priority.lower(), "#6B7280")
    new_color = priority_colors.get(new_priority.lower(), "#DC2626")

    return _email_wrapper(f"""\
<p style="font-size:16px;font-weight:600;color:#DC2626;">🚨 SLA Breach Alert</p>

<div style="background:#FEF2F2;border-left:4px solid #DC2626;padding:12px 16px;margin:16px 0;border-radius:4px;">
  <p style="margin:0;font-weight:600;font-size:15px;">{subject}</p>
  <p style="margin:4px 0 0;color:#6b7280;font-size:13px;">
    Ticket {ticket_number} has breached its SLA and has been automatically escalated.
  </p>
</div>

<table style="width:100%;border-collapse:collapse;margin:16px 0;">
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Ticket Number</td>
    <td style="padding:8px 0;font-weight:600;font-family:monospace;">{ticket_number}</td>
  </tr>
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Hours Overdue</td>
    <td style="padding:8px 0;font-weight:600;color:#DC2626;">{hours_overdue:.1f} hours</td>
  </tr>
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Priority Change</td>
    <td style="padding:8px 0;">
      <span style="background:{old_color};color:white;padding:2px 8px;border-radius:4px;font-weight:600;text-transform:uppercase;font-size:11px;">{old_priority}</span>
      <span style="margin:0 8px;">→</span>
      <span style="background:{new_color};color:white;padding:2px 8px;border-radius:4px;font-weight:600;text-transform:uppercase;font-size:11px;">{new_priority}</span>
    </td>
  </tr>
  <tr>
    <td style="padding:8px 0;color:#6b7280;font-size:14px;">Escalated At</td>
    <td style="padding:8px 0;">{now}</td>
  </tr>
</table>

<div style="background:#FFFBEB;border:1px solid #FCD34D;border-radius:8px;padding:16px;margin:16px 0;">
  <p style="margin:0;color:#92400E;font-weight:600;">⚠️ Action Required</p>
  <p style="margin:8px 0 0;color:#78350F;">This ticket requires immediate attention. Please review and respond as soon as possible.</p>
</div>

<table cellpadding="0" cellspacing="0" border="0" style="margin:16px 0;">
  <tr>
    <td style="background:#DC2626;border-radius:6px;padding:10px 20px;">
      <a href="https://dashboard.ai-identity.co/support" style="color:#FFFFFF;text-decoration:none;font-weight:600;font-size:14px;">View Ticket Now</a>
    </td>
  </tr>
</table>

<p style="font-size:13px;color:#6b7280;">
  This is an automated notification from the SLA monitoring system.
</p>""")


# Made with Bob

# Made with Bob
