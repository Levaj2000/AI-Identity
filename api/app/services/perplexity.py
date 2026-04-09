"""Perplexity AI client for structured audit log summarisation (v2).

Calls the Perplexity chat-completions API (OpenAI-compatible) with a
fixed JSON report template.  The model fills in the template from
structured event data — producing consistent, parseable output that is
rendered directly in the dashboard without markdown processing.

The feature is gated on ``settings.perplexity_api_key`` — when empty
the endpoint returns 503.
"""

import json
import logging

import httpx

from common.config.settings import settings

logger = logging.getLogger("ai_identity.services.perplexity")

_SYSTEM_PROMPT = """\
You are a security audit analyst writing concise enterprise-grade summaries \
for AI agent activity.

Your job is to analyze the provided audit event data and produce a report \
for a product UI.

Follow these rules exactly:
- Use only the facts provided in the audit event data.
- Do not invent missing details.
- If evidence is limited, say "based on the events reviewed in this audit window".
- Separate observed facts from interpretation.
- Keep the tone precise, calm, and professional.
- Do not use hype, marketing language, or dramatic wording.
- Do not claim malicious behavior unless the evidence clearly supports it.
- If there are zero denied requests and zero errors, do not overstate risk.
- Recommendations must be operational and specific.
- The audit record is the primary evidence. Do not reference external URLs, \
web sources, or citation numbers. Ground all statements in the provided data.
- Output valid JSON only. No markdown fences, no commentary outside the JSON.

Return JSON in this exact shape:
{
  "title": "AI Agent Audit Summary",
  "executive_summary": "string — 2-4 sentence overview of the audit window",
  "observed_facts": [
    {"label": "string — fact name", "value": "string — fact value"}
  ],
  "assessment": "string — interpretation of the observed facts, 2-4 sentences",
  "recommended_follow_ups": [
    "string — actionable recommendation"
  ],
  "risk_level": "informational|low|medium|high",
  "confidence": "low|medium|high"
}
"""


class PerplexityError(Exception):
    """Raised when the Perplexity API returns an error."""


def summarize_audit_events(
    event_data: dict,
) -> dict:
    """Call Perplexity to produce a structured audit summary.

    Parameters
    ----------
    event_data:
        Normalized event object (dict) with structured audit fields.

    Returns
    -------
    dict
        Parsed JSON report dict.

    Raises
    ------
    PerplexityError
        On any API-level failure (timeout, HTTP error, bad response).
    """
    if not settings.perplexity_api_key:
        raise PerplexityError("Perplexity API key not configured")

    user_message = f"Audit event data:\n{json.dumps(event_data, indent=2)}"

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

    # Parse the JSON report from the model response
    # Strip markdown code fences if present (```json ... ```)
    cleaned = content.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (```json or ```)
        first_newline = cleaned.index("\n")
        cleaned = cleaned[first_newline + 1 :]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        report = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Perplexity response as JSON: %s", exc)
        logger.debug("Raw response content: %s", content[:500])
        raise PerplexityError("AI returned an invalid response format. Please try again.") from exc

    # Validate required fields are present
    required_fields = (
        "title",
        "executive_summary",
        "observed_facts",
        "assessment",
        "recommended_follow_ups",
        "risk_level",
        "confidence",
    )
    missing = [f for f in required_fields if f not in report]
    if missing:
        logger.error("Perplexity response missing fields: %s", missing)
        raise PerplexityError("AI returned an incomplete response. Please try again.") from None

    return report
