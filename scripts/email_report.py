#!/usr/bin/env python3
"""Email a generated report (PDF / markdown / text) to a recipient via Resend.

This is the default delivery mechanism for AI Identity reports — the
`standards-architect` R&D reports and the scheduled standards-scan all route
through here. Default recipient is the founder (jeff@ai-identity.co); override
with --to.

Usage:
    python scripts/email_report.py FILE [FILE2 ...] [--to addr] [--subject S] [--note TEXT]

Reads RESEND_API_KEY from the environment or the repo .env. No-ops with a clear
message (exit 2) if the key is unset, so callers can degrade gracefully.

Examples:
    python scripts/email_report.py docs/strategy/ai-identity-rd-horizon-2030-report-2026-06-09.pdf
    python scripts/email_report.py /tmp/standards-scan.md --subject "Weekly standards scan"
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Default recipient for all generated reports. See feedback_report_email_default memory.
DEFAULT_REPORT_RECIPIENT = "jeff@ai-identity.co"
DEFAULT_FROM = "AI Identity Reports <jeff@ai-identity.co>"


def _load_resend_api_key() -> str:
    key = os.getenv("RESEND_API_KEY", "").strip()
    if key:
        return key
    env_file = Path(__file__).resolve().parents[1] / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("RESEND_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Email a report via Resend.")
    ap.add_argument("files", nargs="+", help="Report file(s) to attach.")
    ap.add_argument("--to", default=DEFAULT_REPORT_RECIPIENT, help="Recipient email.")
    ap.add_argument("--subject", default=None, help="Subject (defaults to the file names).")
    ap.add_argument("--note", default="", help="Optional intro line in the body.")
    args = ap.parse_args(argv)

    files = [Path(f) for f in args.files]
    missing = [str(f) for f in files if not f.exists()]
    if missing:
        print(f"email_report: file(s) not found: {missing}", file=sys.stderr)
        return 2

    api_key = _load_resend_api_key()
    if not api_key:
        print(
            "email_report: RESEND_API_KEY not set — cannot send. Add it to the repo .env "
            "(or the environment) and re-run. The same key is configured on the API in prod.",
            file=sys.stderr,
        )
        return 2

    import resend

    resend.api_key = api_key

    attachments = [{"filename": f.name, "content": list(f.read_bytes())} for f in files]
    subject = args.subject or ("AI Identity report: " + ", ".join(f.stem for f in files))
    body = []
    if args.note:
        body.append(f"<p>{args.note}</p>")
    body.append("<p>Attached:</p><ul>" + "".join(f"<li>{f.name}</li>" for f in files) + "</ul>")
    html = "".join(body)

    try:
        result = resend.Emails.send(
            {
                "from": os.getenv("RESEND_FROM_EMAIL", DEFAULT_FROM),
                "to": [args.to],
                "subject": subject,
                "html": html,
                "attachments": attachments,
            }
        )
        rid = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        print(f"email_report: sent to {args.to} (resend_id={rid})")
        return 0
    except Exception as e:  # noqa: BLE001 — surface any send failure to the caller
        print(f"email_report: send failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
