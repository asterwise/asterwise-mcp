"""Shared async httpx client: retries, per-call timeouts, structured logs."""

from __future__ import annotations

import asyncio
import logging
import os
import random
import time
import uuid
from typing import Any
from urllib.parse import quote

import httpx

from errors import AsterwiseAPIError, map_http_status_to_message

logger = logging.getLogger("asterwise_mcp")

MAX_RETRIES = 3
BASE_DELAY = 0.5
MAX_DELAY = 8.0

_NON_RETRYABLE_STATUS = frozenset({400, 401, 403, 404, 422})
_RETRYABLE_STATUS = frozenset({502, 503, 504})


def safe_segment(value: str) -> str:
    """URL-encode a single path segment safely."""
    return quote(str(value).strip(), safe="")


# Backward compatibility
_safe_path_segment = safe_segment


class AsterwiseClient:
    """Process-wide HTTP client — opened in app lifespan."""

    def __init__(self) -> None:
        raw = os.getenv("ASTERWISE_API_BASE_URL")
        if not raw:
            raise RuntimeError(
                "ASTERWISE_API_BASE_URL is not set. Configure the Asterwise API base URL "
                "(e.g. https://api.asterwise.com)."
            )
        self.base_url = raw.rstrip("/")
        self._default_timeout = 30.0
        self._http: httpx.AsyncClient | None = None

    async def open(self) -> None:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self._default_timeout,
                headers={
                    "User-Agent": "asterwise-mcp/1.0",
                    "Accept": "application/json",
                },
            )

    async def close(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            raise RuntimeError("AsterwiseClient is not initialized; check app lifespan.")
        return self._http

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        detail: str | None = None
        try:
            body = response.json()
            if isinstance(body, dict):
                d = body.get("detail")
                if isinstance(d, str):
                    detail = d
                elif isinstance(d, list):
                    parts = []
                    for item in d:
                        if isinstance(item, dict):
                            loc = item.get("loc", ())
                            msg = item.get("msg", "")
                            parts.append(f"{loc}: {msg}" if loc else str(msg))
                        else:
                            parts.append(str(item))
                    detail = "; ".join(parts) if parts else str(d)
        except Exception:
            text = response.text
            if text:
                detail = text[:500]
        msg = map_http_status_to_message(response.status_code, detail)
        raise AsterwiseAPIError(msg, hint=msg)

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        api_key: str,
        *,
        timeout: float,
        **kwargs: Any,
    ) -> dict[str, Any]:
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()
        headers = {
            "X-API-Key": api_key,
            "User-Agent": "asterwise-mcp/1.0",
            "Accept": "application/json",
        }
        last_error: BaseException | None = None

        logger.info(
            "upstream_request",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
            },
        )

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await self._client().request(
                    method,
                    path,
                    headers=headers,
                    timeout=httpx.Timeout(timeout),
                    **kwargs,
                )

                if response.status_code in _NON_RETRYABLE_STATUS:
                    self._raise_for_status(response)

                if response.status_code == 429:
                    if attempt < MAX_RETRIES:
                        ra = response.headers.get("Retry-After")
                        try:
                            delay = float(ra) if ra is not None else BASE_DELAY * (2**attempt)
                        except (TypeError, ValueError):
                            delay = BASE_DELAY * (2**attempt)
                        delay = min(delay + random.uniform(0, 0.5), MAX_DELAY)
                        logger.warning(
                            "upstream_retry",
                            extra={
                                "request_id": request_id,
                                "attempt": attempt + 1,
                                "reason": "429",
                                "delay": round(delay, 2),
                                "path": path,
                            },
                        )
                        await asyncio.sleep(delay)
                        continue
                    self._raise_for_status(response)

                if response.status_code in _RETRYABLE_STATUS:
                    if attempt < MAX_RETRIES:
                        delay = min(
                            BASE_DELAY * (2**attempt) + random.uniform(0, 0.5),
                            MAX_DELAY,
                        )
                        logger.warning(
                            "upstream_retry",
                            extra={
                                "request_id": request_id,
                                "attempt": attempt + 1,
                                "reason": str(response.status_code),
                                "delay": round(delay, 2),
                                "path": path,
                            },
                        )
                        await asyncio.sleep(delay)
                        continue
                    self._raise_for_status(response)

                if not response.is_success:
                    self._raise_for_status(response)

                elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
                logger.info(
                    "upstream_success",
                    extra={
                        "request_id": request_id,
                        "path": path,
                        "status": response.status_code,
                        "elapsed_ms": elapsed_ms,
                    },
                )
                data = response.json()
                if not isinstance(data, dict):
                    return {"data": data}
                return data

            except AsterwiseAPIError:
                raise

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    delay = min(
                        BASE_DELAY * (2**attempt) + random.uniform(0, 0.5),
                        MAX_DELAY,
                    )
                    logger.warning(
                        "upstream_retry",
                        extra={
                            "request_id": request_id,
                            "attempt": attempt + 1,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "delay": round(delay, 2),
                            "path": path,
                        },
                    )
                    await asyncio.sleep(delay)
                    continue
                elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
                logger.error(
                    "upstream_failure",
                    extra={
                        "request_id": request_id,
                        "path": path,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "elapsed_ms": elapsed_ms,
                    },
                )
                raise

            except Exception as e:
                elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
                logger.error(
                    "upstream_failure",
                    extra={
                        "request_id": request_id,
                        "path": path,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "elapsed_ms": elapsed_ms,
                    },
                )
                raise

        if last_error is not None:
            raise last_error
        raise RuntimeError("request retry loop exited without result")

    async def post(
        self,
        path: str,
        api_key: str,
        body: dict[str, Any],
        *,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        """POST JSON to Asterwise API."""
        return await self._request_with_retry(
            "POST", path, api_key, timeout=timeout, json=body
        )

    async def get(
        self,
        path: str,
        api_key: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        """GET from Asterwise API."""
        return await self._request_with_retry(
            "GET", path, api_key, timeout=timeout, params=params or {}
        )


_client_singleton: AsterwiseClient | None = None


def get_client() -> AsterwiseClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = AsterwiseClient()
    return _client_singleton
