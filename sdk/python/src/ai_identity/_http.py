"""Low-level HTTP client for the AI Identity API."""

from __future__ import annotations

from typing import Any

import httpx

from ai_identity.exceptions import (
    AIIdentityError,
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)

_ERROR_MAP: dict[int, type[AIIdentityError]] = {
    401: AuthenticationError,
    403: ForbiddenError,
    404: NotFoundError,
    422: ValidationError,
    429: RateLimitError,
}


class HTTPClient:
    """Async HTTP client that injects auth and maps errors."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout: float = 30.0,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json",
                "User-Agent": "ai-identity-python/0.1.0",
            },
            timeout=timeout,
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Send a request and return the parsed JSON response."""
        # Strip None values from query params
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        response = await self._client.request(
            method,
            path,
            json=json,
            params=params,
        )

        if response.status_code >= 400:
            self._raise_error(response)

        if response.status_code == 204:
            return None

        return response.json()

    def _raise_error(self, response: httpx.Response) -> None:
        """Parse the API error response and raise a typed exception."""
        status = response.status_code
        error_code = "unknown_error"
        message = f"HTTP {status}"

        try:
            body = response.json()
            if "error" in body:
                error_code = body["error"].get("code", error_code)
                message = body["error"].get("message", message)
            elif "detail" in body:
                message = str(body["detail"])
        except Exception:
            message = response.text or message

        exc_class = _ERROR_MAP.get(status, AIIdentityError)
        raise exc_class(message, status_code=status, error_code=error_code)

    async def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, *, json: dict | None = None) -> Any:
        return await self.request("POST", path, json=json)

    async def put(self, path: str, *, json: dict | None = None) -> Any:
        return await self.request("PUT", path, json=json)

    async def patch(self, path: str, *, json: dict | None = None) -> Any:
        return await self.request("PATCH", path, json=json)

    async def delete(self, path: str) -> Any:
        return await self.request("DELETE", path)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
