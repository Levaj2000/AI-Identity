"""Perplexity AI client for audit log summarisation.

Calls the Perplexity chat-completions API (OpenAI-compatible) to produce
natural-language summaries of agent activity.  The feature is gated on
``settings.perplexity_api_key`` — when empty the endpoint returns 503.
"""

import logging

import httpx

from common.config.settings import settings

logger = logging.getLogger("ai_identity.services.perplexity")

_SYSTEM_PROMPT = """\
You are an AI security analyst reviewing audit logs from an AI agent \
governance platform called AI Identity.

Analyze the provided agent activity and produce a clear, actionable summary \
using the following sections:

## Overview
Brief description of what happened in this time window.

## Key Activity
Most significant actions, patterns, and endpoints used.

## Anomalies & Concerns
Any unusual patterns — denied requests, error spikes, cost outliers, \
latency anomalies, or potential security issues.  If nothing stands out, \
say so.

## Recommendations
Actionable next steps based on best practices for AI agent governance.  \
Reference relevant security frameworks (NIST AI RMF, OWASP LLM Top 10, \
SOC 2) where applicable and link to authoritative sources.

Keep the summary concise but thorough.  Use bullet points for readability.
"""


class PerplexityError(Exception):
    """Raised when the Perplexity API returns an error."""


def summarize_audit_events(
    events_text: str,
    stats_summary: str,
    agent_name: str | None = None,
) -> tuple[str, list[str]]:
    """Call Perplexity to summarise formatted audit events.

    Parameters
    ----------
    events_text:
        Pre-formatted audit log lines (one per event).
    stats_summary:
        Aggregated stats block (counts, cost, latency, top endpoints).
    agent_name:
        Optional agent name for context.

    Returns
    -------
    tuple[str, list[str]]
        (Markdown-formatted summary, list of citation URLs).

    Raises
    ------
    PerplexityError
        On any API-level failure (timeout, HTTP error, bad response).
    """
    if not settings.perplexity_api_key:
        raise PerplexityError("Perplexity API key not configured")

    context = f"Agent: {agent_name}\n\n" if agent_name else ""
    user_message = (
        f"{context}Audit statistics:\n{stats_summary}\n\nAgent activity log:\n{events_text}"
    )

    payload = {
        "model": settings.perplexity_model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                "https://api.perplexity.ai/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.perplexity_api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
    except httpx.TimeoutException as exc:
        logger.warning("Perplexity API request timed out")
        raise PerplexityError("Summary generation timed out — please try again") from exc
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Perplexity API error: %s %s", exc.response.status_code, exc.response.text[:200]
        )
        if exc.response.status_code == 429:
            raise PerplexityError("Perplexity rate limit reached — please try again later") from exc
        raise PerplexityError("AI service temporarily unavailable") from exc
    except httpx.HTTPError as exc:
        logger.warning("Perplexity HTTP error: %s", exc)
        raise PerplexityError("AI service temporarily unavailable") from exc

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        logger.error("Unexpected Perplexity response shape: %s", exc)
        raise PerplexityError("Unexpected response from AI service") from exc

    citations: list[str] = data.get("citations") or []
    return content, citations
