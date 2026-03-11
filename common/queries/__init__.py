"""Shared database query helpers used by api/ and gateway/."""

from common.queries.agents import get_user_agent

__all__ = [
    "get_user_agent",
]
