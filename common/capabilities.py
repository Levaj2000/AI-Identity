"""Predefined capability registry — maps capability IDs to gateway policy rules.

Each capability defines which API endpoints an agent is allowed to access.
When capabilities are assigned to an agent, a policy is auto-generated from
the union of all selected capabilities' endpoint/method mappings.

This is the single source of truth — the dashboard fetches these definitions
via GET /api/v1/capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CapabilityDefinition:
    """A predefined capability with its endpoint permission mappings."""

    id: str
    name: str
    description: str
    endpoints: tuple[str, ...] = field(default_factory=tuple)
    methods: tuple[str, ...] = field(default_factory=tuple)


# ── Registry ────────────────────────────────────────────────────────────

CAPABILITY_REGISTRY: dict[str, CapabilityDefinition] = {
    "openai_chat": CapabilityDefinition(
        id="openai_chat",
        name="OpenAI Chat Completions",
        description="Access to the OpenAI chat completions endpoint for conversational AI",
        endpoints=("/v1/chat/completions",),
        methods=("POST",),
    ),
    "openai_embeddings": CapabilityDefinition(
        id="openai_embeddings",
        name="OpenAI Embeddings",
        description="Access to the OpenAI embeddings endpoint for vector generation",
        endpoints=("/v1/embeddings",),
        methods=("POST",),
    ),
    "openai_images": CapabilityDefinition(
        id="openai_images",
        name="OpenAI Image Generation",
        description="Access to the OpenAI image generation endpoint (DALL-E)",
        endpoints=("/v1/images/generations",),
        methods=("POST",),
    ),
    "anthropic_messages": CapabilityDefinition(
        id="anthropic_messages",
        name="Anthropic Messages",
        description="Access to the Anthropic messages endpoint for Claude-powered agents",
        endpoints=("/v1/messages",),
        methods=("POST",),
    ),
    "web_search": CapabilityDefinition(
        id="web_search",
        name="Web Search",
        description="Access to web search endpoints for retrieval-augmented generation",
        endpoints=("/v1/search/*",),
        methods=("GET", "POST"),
    ),
}


# ── Helpers ──────────────────────────────────────────────────────────────


def get_predefined_capability_ids() -> list[str]:
    """Return sorted list of all predefined capability IDs."""
    return sorted(CAPABILITY_REGISTRY.keys())


def build_policy_rules_from_capabilities(
    capability_ids: list[str],
) -> dict | None:
    """Build gateway policy rules from a list of capability IDs.

    Returns the union of all matched capabilities' endpoints and methods
    as a policy rules dict, or None if no predefined capabilities match.

    Unknown capability IDs are silently ignored for backward compatibility
    with legacy free-text capabilities.
    """
    endpoints: list[str] = []
    methods: set[str] = set()

    for cap_id in capability_ids:
        defn = CAPABILITY_REGISTRY.get(cap_id)
        if defn is None:
            continue
        for ep in defn.endpoints:
            if ep not in endpoints:
                endpoints.append(ep)
        methods.update(defn.methods)

    if not endpoints:
        return None

    return {
        "allowed_endpoints": endpoints,
        "allowed_methods": sorted(methods),
    }
