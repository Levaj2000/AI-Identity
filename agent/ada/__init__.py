"""Ada — AI Identity's senior software engineer agent.

Built on Google ADK. Ada has tools to read the codebase, search it,
list project structure, and query AI Identity's own API — making this
the first agent to dogfood the AI Identity platform.
"""

from . import agent

__all__ = ["agent"]
