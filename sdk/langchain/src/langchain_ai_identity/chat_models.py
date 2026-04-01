"""AIIdentityChatOpenAI — drop-in ChatOpenAI replacement with gateway enforcement.

Routes every chat completion request through the AI Identity gateway for
policy enforcement before forwarding to OpenAI.  Automatically injects the
:class:`~langchain_ai_identity.callback.AIIdentityCallbackHandler` for audit
logging, so you get both enforcement *and* a tamper-proof audit trail with
zero extra setup.
"""

from __future__ import annotations

import logging
import warnings
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI

from langchain_ai_identity.callback import AIIdentityCallbackHandler

logger = logging.getLogger(__name__)

AI_IDENTITY_GATEWAY_BASE = "https://ai-identity-gateway.onrender.com"
_ENFORCE_ENDPOINT = f"{AI_IDENTITY_GATEWAY_BASE}/gateway/enforce"
_DEFAULT_TIMEOUT = 5.0

# The logical endpoint label used when checking LLM access
_LLM_ENDPOINT = "/v1/chat/completions"


def _enforce_llm_access(
    api_key: str,
    agent_id: str,
    fail_closed: bool,
    timeout: float,
) -> None:
    """Call the gateway to enforce LLM access policy.

    Args:
        api_key: Agent runtime key (``aid_sk_...``).
        agent_id: UUID of the requesting agent.
        fail_closed: Raise on denial or gateway error when ``True``.
        timeout: HTTP timeout in seconds.

    Raises:
        PermissionError: If the gateway denies the request and ``fail_closed=True``.
        RuntimeError: If the gateway is unreachable and ``fail_closed=True``.
    """
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                _ENFORCE_ENDPOINT,
                params={
                    "agent_id": agent_id,
                    "endpoint": _LLM_ENDPOINT,
                    "method": "POST",
                    "key_type": "runtime",
                },
                headers={"X-API-Key": api_key},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        msg = f"[AI Identity] Gateway returned HTTP {exc.response.status_code} for {_LLM_ENDPOINT}"
        logger.error(msg)
        if fail_closed:
            raise PermissionError(msg) from exc
        warnings.warn(msg, stacklevel=4)
        return
    except Exception as exc:  # noqa: BLE001
        msg = f"[AI Identity] Gateway unreachable: {exc}"
        logger.error(msg)
        if fail_closed:
            raise RuntimeError(msg) from exc
        warnings.warn(msg, stacklevel=4)
        return

    decision = data.get("decision", "deny")
    if decision != "allow":
        reason = data.get("reason", "No reason provided by policy engine")
        msg = f"[AI Identity] LLM call denied by policy: {reason}"
        if fail_closed:
            raise PermissionError(msg)
        warnings.warn(msg, stacklevel=4)


async def _enforce_llm_access_async(
    api_key: str,
    agent_id: str,
    fail_closed: bool,
    timeout: float,
) -> None:
    """Async version of :func:`_enforce_llm_access`."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                _ENFORCE_ENDPOINT,
                params={
                    "agent_id": agent_id,
                    "endpoint": _LLM_ENDPOINT,
                    "method": "POST",
                    "key_type": "runtime",
                },
                headers={"X-API-Key": api_key},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        msg = f"[AI Identity] Gateway returned HTTP {exc.response.status_code} for {_LLM_ENDPOINT}"
        logger.error(msg)
        if fail_closed:
            raise PermissionError(msg) from exc
        warnings.warn(msg, stacklevel=4)
        return
    except Exception as exc:  # noqa: BLE001
        msg = f"[AI Identity] Gateway unreachable: {exc}"
        logger.error(msg)
        if fail_closed:
            raise RuntimeError(msg) from exc
        warnings.warn(msg, stacklevel=4)
        return

    decision = data.get("decision", "deny")
    if decision != "allow":
        reason = data.get("reason", "No reason provided by policy engine")
        msg = f"[AI Identity] LLM call denied by policy: {reason}"
        if fail_closed:
            raise PermissionError(msg)
        warnings.warn(msg, stacklevel=4)


class AIIdentityChatOpenAI(ChatOpenAI):
    """Drop-in replacement for :class:`~langchain_openai.ChatOpenAI` that enforces
    AI Identity policy before every LLM call.

    Before forwarding a chat completion request to OpenAI, this class hits the
    AI Identity gateway's ``/gateway/enforce`` endpoint.  If the agent's policy
    denies the call, a :class:`PermissionError` is raised (or a warning is
    emitted when ``fail_closed=False``).

    It also automatically injects the
    :class:`~langchain_ai_identity.callback.AIIdentityCallbackHandler` so every
    LLM call and response is recorded in the AI Identity audit log.

    Example::

        from langchain_ai_identity import AIIdentityChatOpenAI

        llm = AIIdentityChatOpenAI(
            agent_id="<your-agent-uuid>",
            ai_identity_api_key="aid_sk_...",
            openai_api_key="sk-...",
            model="gpt-4o",
        )
        response = llm.invoke("Tell me about AI security.")

    Args:
        agent_id: UUID of the registered AI Identity agent.
        ai_identity_api_key: The ``aid_sk_`` prefixed key returned at agent creation.
        fail_closed: When ``True`` (default), a gateway denial or error raises
            an exception.  When ``False``, a warning is logged and the call
            proceeds (fail-open mode).
        ai_identity_timeout: HTTP timeout for gateway calls in seconds (default 5.0).
        **kwargs: All other arguments forwarded to :class:`~langchain_openai.ChatOpenAI`
            (e.g. ``model``, ``temperature``, ``openai_api_key``).
    """

    # Pydantic v2 model fields for the extra params
    agent_id: str
    ai_identity_api_key: str
    fail_closed: bool = True
    ai_identity_timeout: float = _DEFAULT_TIMEOUT

    def __init__(
        self,
        agent_id: str,
        ai_identity_api_key: str,
        fail_closed: bool = True,
        ai_identity_timeout: float = _DEFAULT_TIMEOUT,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            agent_id=agent_id,
            ai_identity_api_key=ai_identity_api_key,
            fail_closed=fail_closed,
            ai_identity_timeout=ai_identity_timeout,
            **kwargs,
        )
        # Inject the audit callback handler automatically
        self._inject_callback_handler()

    def _inject_callback_handler(self) -> None:
        """Add AIIdentityCallbackHandler to this LLM's callback list if not already present."""
        existing_callbacks = list(self.callbacks or [])
        already_present = any(
            isinstance(cb, AIIdentityCallbackHandler) for cb in existing_callbacks
        )
        if not already_present:
            handler = AIIdentityCallbackHandler(
                agent_id=self.agent_id,
                api_key=self.ai_identity_api_key,
                fail_closed=self.fail_closed,
                timeout=self.ai_identity_timeout,
            )
            self.callbacks = existing_callbacks + [handler]

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Enforce policy then generate a chat response synchronously."""
        _enforce_llm_access(
            api_key=self.ai_identity_api_key,
            agent_id=self.agent_id,
            fail_closed=self.fail_closed,
            timeout=self.ai_identity_timeout,
        )
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Enforce policy then generate a chat response asynchronously."""
        await _enforce_llm_access_async(
            api_key=self.ai_identity_api_key,
            agent_id=self.agent_id,
            fail_closed=self.fail_closed,
            timeout=self.ai_identity_timeout,
        )
        return await super()._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> Iterator[Any]:
        """Enforce policy then stream a chat response."""
        _enforce_llm_access(
            api_key=self.ai_identity_api_key,
            agent_id=self.agent_id,
            fail_closed=self.fail_closed,
            timeout=self.ai_identity_timeout,
        )
        yield from super()._stream(messages, stop=stop, run_manager=run_manager, **kwargs)

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        """Enforce policy then async-stream a chat response."""
        await _enforce_llm_access_async(
            api_key=self.ai_identity_api_key,
            agent_id=self.agent_id,
            fail_closed=self.fail_closed,
            timeout=self.ai_identity_timeout,
        )
        async for chunk in super()._astream(messages, stop=stop, run_manager=run_manager, **kwargs):
            yield chunk
