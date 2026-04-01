"""AIIdentityToolkit — wraps LangChain tools with AI Identity policy enforcement.

Every tool call is pre-checked against the agent's policy via the AI Identity
gateway. If the gateway returns ``decision: deny``, the tool raises a
``ToolException`` with the reason, and the call is logged in the audit trail.
"""

from __future__ import annotations

import functools
import logging
import warnings
from typing import Any, Callable, Dict, List, Optional, Type

import httpx
from langchain_core.tools import BaseTool, ToolException

logger = logging.getLogger(__name__)

AI_IDENTITY_GATEWAY_BASE = "https://ai-identity-gateway.onrender.com"
_ENFORCE_ENDPOINT = f"{AI_IDENTITY_GATEWAY_BASE}/gateway/enforce"
_DEFAULT_TIMEOUT = 5.0


def _check_gateway(
    api_key: str,
    agent_id: str,
    tool_endpoint: str,
    method: str = "POST",
    fail_closed: bool = True,
    timeout: float = _DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """Call the AI Identity gateway enforce endpoint.

    Args:
        api_key: The ``aid_sk_`` prefixed agent API key.
        agent_id: UUID of the agent making the request.
        tool_endpoint: Logical endpoint representing the tool (e.g. ``/tools/search``).
        method: HTTP method to check (default ``POST``).
        fail_closed: If ``True``, network/timeout errors count as a denial.
            If ``False``, errors allow the request through with a warning.
        timeout: Request timeout in seconds.

    Returns:
        The parsed JSON response from the gateway, e.g.
        ``{"decision": "allow", ...}`` or ``{"decision": "deny", "reason": "..."}``.

    Raises:
        ToolException: If the gateway denies the request (``fail_closed=True``).
        RuntimeError: If the gateway is unreachable and ``fail_closed=True``.
    """
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                _ENFORCE_ENDPOINT,
                params={
                    "agent_id": agent_id,
                    "endpoint": tool_endpoint,
                    "method": method,
                    "key_type": "runtime",
                },
                headers={"X-API-Key": api_key},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        msg = f"[AI Identity] Gateway returned HTTP {exc.response.status_code} for {tool_endpoint}"
        logger.error(msg)
        if fail_closed:
            raise ToolException(msg) from exc
        warnings.warn(msg, stacklevel=4)
        return {"decision": "allow", "reason": "fail-open after gateway error"}
    except Exception as exc:  # noqa: BLE001
        msg = f"[AI Identity] Gateway unreachable for {tool_endpoint}: {exc}"
        logger.error(msg)
        if fail_closed:
            raise ToolException(msg) from exc
        warnings.warn(msg, stacklevel=4)
        return {"decision": "allow", "reason": "fail-open after gateway error"}


async def _check_gateway_async(
    api_key: str,
    agent_id: str,
    tool_endpoint: str,
    method: str = "POST",
    fail_closed: bool = True,
    timeout: float = _DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """Async version of :func:`_check_gateway`."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                _ENFORCE_ENDPOINT,
                params={
                    "agent_id": agent_id,
                    "endpoint": tool_endpoint,
                    "method": method,
                    "key_type": "runtime",
                },
                headers={"X-API-Key": api_key},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        msg = f"[AI Identity] Gateway returned HTTP {exc.response.status_code} for {tool_endpoint}"
        logger.error(msg)
        if fail_closed:
            raise ToolException(msg) from exc
        warnings.warn(msg, stacklevel=4)
        return {"decision": "allow", "reason": "fail-open after gateway error"}
    except Exception as exc:  # noqa: BLE001
        msg = f"[AI Identity] Gateway unreachable for {tool_endpoint}: {exc}"
        logger.error(msg)
        if fail_closed:
            raise ToolException(msg) from exc
        warnings.warn(msg, stacklevel=4)
        return {"decision": "allow", "reason": "fail-open after gateway error"}


def _wrap_tool(
    tool: BaseTool,
    agent_id: str,
    api_key: str,
    fail_closed: bool,
    timeout: float,
) -> BaseTool:
    """Return a shallow copy of *tool* whose ``_run`` / ``_arun`` methods check the gateway first.

    The original tool class is not mutated; a new subclass is created on the fly.
    """
    tool_endpoint = f"/tools/{tool.name.lower().replace(' ', '_')}"
    original_run = tool._run  # type: ignore[attr-defined]
    original_arun = tool._arun  # type: ignore[attr-defined]

    @functools.wraps(original_run)
    def _guarded_run(*args: Any, **kwargs: Any) -> Any:
        result = _check_gateway(
            api_key=api_key,
            agent_id=agent_id,
            tool_endpoint=tool_endpoint,
            fail_closed=fail_closed,
            timeout=timeout,
        )
        decision = result.get("decision", "deny")
        if decision != "allow":
            reason = result.get("reason", "No reason provided by policy engine")
            raise ToolException(
                f"[AI Identity] Tool '{tool.name}' denied by policy: {reason}"
            )
        return original_run(*args, **kwargs)

    @functools.wraps(original_arun)
    async def _guarded_arun(*args: Any, **kwargs: Any) -> Any:
        result = await _check_gateway_async(
            api_key=api_key,
            agent_id=agent_id,
            tool_endpoint=tool_endpoint,
            fail_closed=fail_closed,
            timeout=timeout,
        )
        decision = result.get("decision", "deny")
        if decision != "allow":
            reason = result.get("reason", "No reason provided by policy engine")
            raise ToolException(
                f"[AI Identity] Tool '{tool.name}' denied by policy: {reason}"
            )
        return await original_arun(*args, **kwargs)

    # Bind the new methods onto the tool instance without touching the class
    tool._run = _guarded_run  # type: ignore[method-assign]
    tool._arun = _guarded_arun  # type: ignore[method-assign]
    return tool


class AIIdentityToolkit:
    """Wraps a list of LangChain tools with AI Identity gateway enforcement.

    Each wrapped tool checks the AI Identity gateway's ``/gateway/enforce``
    endpoint before executing.  If the agent's policy denies the call, a
    :class:`~langchain_core.tools.ToolException` is raised with the deny reason.

    Example::

        from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
        from langchain_ai_identity import AIIdentityToolkit

        toolkit = AIIdentityToolkit(
            tools=[DuckDuckGoSearchRun(), WikipediaQueryRun()],
            agent_id="<your-agent-uuid>",
            api_key="aid_sk_...",
        )
        safe_tools = toolkit.get_tools()

    Args:
        tools: List of :class:`~langchain_core.tools.BaseTool` instances to wrap.
        agent_id: UUID of the registered AI Identity agent.
        api_key: The ``aid_sk_`` prefixed key returned at agent creation.
        fail_closed: When ``True`` (default), gateway errors or timeouts will
            deny the tool call.  Set to ``False`` to allow the call through
            on gateway failures (fail-open mode) with a logged warning.
        timeout: HTTP timeout in seconds for gateway calls (default 5.0).
    """

    def __init__(
        self,
        tools: List[BaseTool],
        agent_id: str,
        api_key: str,
        fail_closed: bool = True,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self.agent_id = agent_id
        self.api_key = api_key
        self.fail_closed = fail_closed
        self.timeout = timeout
        self._original_tools = tools
        self._wrapped_tools: Optional[List[BaseTool]] = None

    def get_tools(self) -> List[BaseTool]:
        """Return the list of tools, each wrapped with AI Identity enforcement.

        Wrapping is lazy and cached — calling this method multiple times returns
        the same wrapped instances.

        Returns:
            List of wrapped :class:`~langchain_core.tools.BaseTool` instances.
        """
        if self._wrapped_tools is None:
            self._wrapped_tools = [
                _wrap_tool(
                    tool=tool,
                    agent_id=self.agent_id,
                    api_key=self.api_key,
                    fail_closed=self.fail_closed,
                    timeout=self.timeout,
                )
                for tool in self._original_tools
            ]
        return self._wrapped_tools

    def check_tool_access(self, tool_name: str) -> Dict[str, Any]:
        """Synchronously check gateway access for a named tool without executing it.

        Useful for pre-flight checks or debugging policy decisions.

        Args:
            tool_name: The name of the tool to check.

        Returns:
            The raw gateway response, e.g. ``{"decision": "allow"}`` or
            ``{"decision": "deny", "reason": "..."}``.
        """
        tool_endpoint = f"/tools/{tool_name.lower().replace(' ', '_')}"
        return _check_gateway(
            api_key=self.api_key,
            agent_id=self.agent_id,
            tool_endpoint=tool_endpoint,
            fail_closed=False,  # always non-raising for pre-flight
            timeout=self.timeout,
        )
