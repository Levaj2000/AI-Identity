"""Transactional email via Resend.

Sends welcome and follow-up emails to new users.
Gracefully no-ops when RESEND_API_KEY is not configured.
"""

import logging

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
    """5-day follow-up email — check-in and quick questions."""
    return _email_wrapper(f"""\
<p>Hi {name},</p>

<p>It's been a few days since you signed up. I wanted to check in and see how things are going.</p>

<p><strong>Three quick questions</strong> (just reply inline):</p>
<ol style="padding-left:20px;color:#374151;">
  <li>Have you created your first agent yet?</li>
  <li>What's your biggest question so far?</li>
  <li>Is anything missing or confusing?</li>
</ol>

<p>If you haven't had a chance to explore yet, here's the fastest path:</p>
<ol style="padding-left:20px;color:#374151;font-size:14px;">
  <li>Log into the <a href="https://dashboard.ai-identity.co" style="color:#F59E0B;">dashboard</a></li>
  <li>Create an agent (takes 30 seconds)</li>
  <li>Set a gateway policy for your agent</li>
  <li>Run the automated compliance check</li>
</ol>

<p>Your feedback directly shapes the product. I read every reply.</p>

<p>
  Jeff<br>
  <span style="color:#6b7280;font-size:13px;">Founder, AI Identity</span>
</p>""")
