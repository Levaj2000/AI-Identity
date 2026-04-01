"""LangChain callback handler that logs events to the AI Identity audit log.

Every LLM call, tool invocation, and chain error is recorded as a tamper-proof
audit entry in AI Identity, giving you a cryptographically verifiable trail of
everything your agent did.
"""

from __future__ import annotations

import asyncio
import logging
import time
import warnings
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import httpx
from langchain_core.callbacks import AsyncCallbackHandler, BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)

AI_IDENTITY_API_BASE = "https://ai-identity-api.onrender.com"
_AUDIT_ENDPOINT = f"{AI_IDENTITY_API_BASE}/api/v1/audit"
_DEFAULT_TIMEOUT = 5.0  # seconds


def _post_audit_sync(
    api_key: str,
    agent_id: str,
    event_type: str,
    endpoint: str,
    decision: str,
    metadata: Optional[Dict[str, Any]] = None,
    latency_ms: Optional[float] = None,
    fail_closed: bool = True,
) -> None:
    """Fire-and-forget synchronous audit POST to AI Identity.

    Args:
        api_key: The ``aid_sk_`` prefixed agent API key.
        agent_id: UUID of the agent being audited.
        event_type: Short label for the event (e.g. ``llm_start``).
        endpoint: The logical endpoint being called (e.g. ``/v1/chat/completions``).
        decision: ``"allowed"``, ``"denied"``, or ``"error"``.
        metadata: Optional dict of extra fields to attach to the log entry.
        latency_ms: Optional request latency in milliseconds.
        fail_closed: If ``True``, re-raises errors from the audit call.
                     If ``False``, logs a warning and continues silently.
    """
    payload: Dict[str, Any] = {
        "agent_id": agent_id,
        "event_type": event_type,
        "endpoint": endpoint,
        "decision": decision,
        "metadata": {**(metadata or {}), "action_type": event_type},
    }
    if latency_ms is not None:
        payload["latency_ms"] = latency_ms

    try:
        with httpx.Client(timeout=_DEFAULT_TIMEOUT) as client:
            response = client.post(
                _AUDIT_ENDPOINT,
                json=payload,
                headers={"X-API-Key": api_key},
            )
            response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        msg = f"[AI Identity] Audit log failed ({event_type}): {exc}"
        if fail_closed:
            raise RuntimeError(msg) from exc
        warnings.warn(msg, stacklevel=3)
        logger.warning(msg)


async def _post_audit_async(
    api_key: str,
    agent_id: str,
    event_type: str,
    endpoint: str,
    decision: str,
    metadata: Optional[Dict[str, Any]] = None,
    latency_ms: Optional[float] = None,
    fail_closed: bool = True,
) -> None:
    """Async version of :func:`_post_audit_sync`."""
    payload: Dict[str, Any] = {
        "agent_id": agent_id,
        "event_type": event_type,
        "endpoint": endpoint,
        "decision": decision,
        "metadata": {**(metadata or {}), "action_type": event_type},
    }
    if latency_ms is not None:
        payload["latency_ms"] = latency_ms

    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            response = await client.post(
                _AUDIT_ENDPOINT,
                json=payload,
                headers={"X-API-Key": api_key},
            )
            response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        msg = f"[AI Identity] Audit log failed ({event_type}): {exc}"
        if fail_closed:
            raise RuntimeError(msg) from exc
        warnings.warn(msg, stacklevel=3)
        logger.warning(msg)


class AIIdentityCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that writes every agent event to AI Identity audit logs.

    Attach this handler to any LangChain chain, agent, or LLM to get a
    cryptographically chained audit trail of every LLM call, tool invocation,
    and error — queryable from the AI Identity dashboard or API.

    Example::

        from langchain_ai_identity import AIIdentityCallbackHandler

        handler = AIIdentityCallbackHandler(
            agent_id="<your-agent-uuid>",
            api_key="aid_sk_...",
        )
        llm = ChatOpenAI(callbacks=[handler])

    Args:
        agent_id: UUID of the registered AI Identity agent.
        api_key: The ``aid_sk_`` prefixed key returned when the agent was created.
        fail_closed: When ``True`` (default) an audit failure raises an exception,
            halting the chain.  Set to ``False`` to log a warning and continue.
        timeout: HTTP timeout in seconds for audit API calls (default 5.0).
    """

    raise_error = False  # LangChain BaseCallbackHandler flag — we manage our own errors

    def __init__(
        self,
        agent_id: str,
        api_key: str,
        fail_closed: bool = True,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__()
        self.agent_id = agent_id
        self.api_key = api_key
        self.fail_closed = fail_closed
        self.timeout = timeout
        self._llm_start_times: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # LLM events
    # ------------------------------------------------------------------

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Record the start of an LLM call."""
        self._llm_start_times[str(run_id)] = time.monotonic()
        _post_audit_sync(
            api_key=self.api_key,
            agent_id=self.agent_id,
            event_type="llm_start",
            endpoint="/v1/chat/completions",
            decision="allowed",
            metadata={
                "model": serialized.get("kwargs", {}).get("model_name", "unknown"),
                "num_prompts": len(prompts),
                "run_id": str(run_id),
            },
            fail_closed=self.fail_closed,
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Record a successful LLM completion."""
        start = self._llm_start_times.pop(str(run_id), None)
        latency_ms = (time.monotonic() - start) * 1000 if start is not None else None

        token_usage = {}
        if response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})

        _post_audit_sync(
            api_key=self.api_key,
            agent_id=self.agent_id,
            event_type="llm_end",
            endpoint="/v1/chat/completions",
            decision="allowed",
            metadata={
                "run_id": str(run_id),
                "total_tokens": token_usage.get("total_tokens"),
                "prompt_tokens": token_usage.get("prompt_tokens"),
                "completion_tokens": token_usage.get("completion_tokens"),
            },
            latency_ms=latency_ms,
            fail_closed=self.fail_closed,
        )

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Record the start of a tool invocation."""
        self._llm_start_times[f"tool_{run_id}"] = time.monotonic()
        tool_name = serialized.get("name", "unknown_tool")
        _post_audit_sync(
            api_key=self.api_key,
            agent_id=self.agent_id,
            event_type="tool_start",
            endpoint=f"/tools/{tool_name}",
            decision="allowed",
            metadata={
                "tool_name": tool_name,
                "input_preview": input_str[:200],
                "run_id": str(run_id),
            },
            fail_closed=self.fail_closed,
        )

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Record a successful tool completion."""
        start = self._llm_start_times.pop(f"tool_{run_id}", None)
        latency_ms = (time.monotonic() - start) * 1000 if start is not None else None
        _post_audit_sync(
            api_key=self.api_key,
            agent_id=self.agent_id,
            event_type="tool_end",
            endpoint="/tools/completed",
            decision="allowed",
            metadata={
                "run_id": str(run_id),
                "output_preview": str(output)[:200],
            },
            latency_ms=latency_ms,
            fail_closed=self.fail_closed,
        )

    def on_chain_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Record a chain error — always logs, regardless of fail_closed."""
        _post_audit_sync(
            api_key=self.api_key,
            agent_id=self.agent_id,
            event_type="chain_error",
            endpoint="/chain",
            decision="error",
            metadata={
                "run_id": str(run_id),
                "error_type": type(error).__name__,
                "error_message": str(error)[:500],
            },
            fail_closed=False,  # never crash on error logging
        )

    def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Record a tool error."""
        _post_audit_sync(
            api_key=self.api_key,
            agent_id=self.agent_id,
            event_type="tool_error",
            endpoint="/tools/error",
            decision="error",
            metadata={
                "run_id": str(run_id),
                "error_type": type(error).__name__,
                "error_message": str(error)[:500],
            },
            fail_closed=False,  # never crash on error logging
        )


class AIIdentityAsyncCallbackHandler(AsyncCallbackHandler):
    """Async version of :class:`AIIdentityCallbackHandler`.

    Use this handler when running LangChain in an async event loop to avoid
    blocking the loop with synchronous HTTP calls.

    Args:
        agent_id: UUID of the registered AI Identity agent.
        api_key: The ``aid_sk_`` prefixed key returned when the agent was created.
        fail_closed: When ``True`` (default) an audit failure raises an exception.
            Set to ``False`` to log a warning and continue.
        timeout: HTTP timeout in seconds for audit API calls (default 5.0).
    """

    def __init__(
        self,
        agent_id: str,
        api_key: str,
        fail_closed: bool = True,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__()
        self.agent_id = agent_id
        self.api_key = api_key
        self.fail_closed = fail_closed
        self.timeout = timeout
        self._llm_start_times: Dict[str, float] = {}

    async def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._llm_start_times[str(run_id)] = time.monotonic()
        await _post_audit_async(
            api_key=self.api_key,
            agent_id=self.agent_id,
            event_type="llm_start",
            endpoint="/v1/chat/completions",
            decision="allowed",
            metadata={
                "model": serialized.get("kwargs", {}).get("model_name", "unknown"),
                "num_prompts": len(prompts),
                "run_id": str(run_id),
            },
            fail_closed=self.fail_closed,
        )

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        start = self._llm_start_times.pop(str(run_id), None)
        latency_ms = (time.monotonic() - start) * 1000 if start is not None else None
        token_usage = {}
        if response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})
        await _post_audit_async(
            api_key=self.api_key,
            agent_id=self.agent_id,
            event_type="llm_end",
            endpoint="/v1/chat/completions",
            decision="allowed",
            metadata={
                "run_id": str(run_id),
                "total_tokens": token_usage.get("total_tokens"),
            },
            latency_ms=latency_ms,
            fail_closed=self.fail_closed,
        )

    async def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._llm_start_times[f"tool_{run_id}"] = time.monotonic()
        tool_name = serialized.get("name", "unknown_tool")
        await _post_audit_async(
            api_key=self.api_key,
            agent_id=self.agent_id,
            event_type="tool_start",
            endpoint=f"/tools/{tool_name}",
            decision="allowed",
            metadata={
                "tool_name": tool_name,
                "input_preview": input_str[:200],
                "run_id": str(run_id),
            },
            fail_closed=self.fail_closed,
        )

    async def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        start = self._llm_start_times.pop(f"tool_{run_id}", None)
        latency_ms = (time.monotonic() - start) * 1000 if start is not None else None
        await _post_audit_async(
            api_key=self.api_key,
            agent_id=self.agent_id,
            event_type="tool_end",
            endpoint="/tools/completed",
            decision="allowed",
            metadata={"run_id": str(run_id), "output_preview": str(output)[:200]},
            latency_ms=latency_ms,
            fail_closed=self.fail_closed,
        )

    async def on_chain_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        await _post_audit_async(
            api_key=self.api_key,
            agent_id=self.agent_id,
            event_type="chain_error",
            endpoint="/chain",
            decision="error",
            metadata={
                "run_id": str(run_id),
                "error_type": type(error).__name__,
                "error_message": str(error)[:500],
            },
            fail_closed=False,
        )

    async def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        await _post_audit_async(
            api_key=self.api_key,
            agent_id=self.agent_id,
            event_type="tool_error",
            endpoint="/tools/error",
            decision="error",
            metadata={
                "run_id": str(run_id),
                "error_type": type(error).__name__,
                "error_message": str(error)[:500],
            },
            fail_closed=False,
        )
