"""AI Identity API tool — Ada's dogfood hook.

This is the tool that makes Ada the first agent to introspect AI Identity itself.
When Ada is registered as an agent in AI Identity (via the dashboard), her own
API key authenticates this call — meaning Ada literally appears in her own audit
trail. That's the case-study moment.
"""

import os
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://api.ai-identity.co"


def query_ai_identity_agent(agent_id: str) -> dict:
    """Fetch metadata for an agent registered in AI Identity.

    Reads `AI_IDENTITY_API_KEY` and `AI_IDENTITY_API_URL` from the environment.
    The API key should be a developer key (the same one used to create agents
    via `POST /api/v1/agents`).

    Args:
        agent_id: UUID of the agent to look up.

    Returns:
        dict with `status` ("success" | "error") and either `agent` (the full
        agent record) or `error_message`.
    """
    api_key = os.getenv("AI_IDENTITY_API_KEY")
    if not api_key:
        return {
            "status": "error",
            "error_message": (
                "AI_IDENTITY_API_KEY is not set. Set it to a developer key "
                "from the AI Identity dashboard so Ada can authenticate."
            ),
        }

    base_url = os.getenv("AI_IDENTITY_API_URL", DEFAULT_BASE_URL).rstrip("/")
    url = f"{base_url}/api/v1/agents/{agent_id}"

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers={"X-API-Key": api_key})
    except httpx.RequestError as exc:
        return {"status": "error", "error_message": f"request failed: {exc}"}

    if response.status_code == 404:
        return {"status": "error", "error_message": f"agent not found: {agent_id}"}
    if response.status_code == 401:
        return {
            "status": "error",
            "error_message": "AI Identity rejected the API key (401). Check AI_IDENTITY_API_KEY.",
        }
    if response.status_code >= 400:
        return {
            "status": "error",
            "error_message": f"AI Identity returned {response.status_code}: {response.text[:200]}",
        }

    payload: Any = response.json()
    return {"status": "success", "agent": payload}
