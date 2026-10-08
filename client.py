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

from errors import AsterwiseAPIError, details_are_sky_side, map_http_status_to_message
from auth import forwarded_client_ip_headers
from context import get_request_client_ip

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

_MAX_ALLOWED_SHOWN = 15


def _render_details(details: Any) -> str | None:
    """One line per error detail, in either shape the API sends.

    Request validation sends Pydantic items ({"loc", "msg"}); route checks
    send {"field", "issue", "allowed…"}. An item with neither used to render
    as an empty string, which hid the field from the model.
    """
    if isinstance(details, str):
        return details or None
    if not isinstance(details, list) or not details:
        return None
    parts: list[str] = []
    for item in details:
        if not isinstance(item, dict):
            parts.append(str(item))
            continue
        if "msg" in item or "loc" in item:
            loc = ".".join(str(p) for p in item.get("loc", ()) if p not in ("body", "query", "path"))
            msg = str(item.get("msg", ""))
            parts.append(f"{loc}: {msg}" if loc else msg)
            continue
        text = ": ".join(str(item[k]) for k in ("field", "issue") if item.get(k))
        for key, value in item.items():
            if key.startswith("allowed") and isinstance(value, list):
                shown = ", ".join(str(v) for v in value[:_MAX_ALLOWED_SHOWN])
                more = "…" if len(value) > _MAX_ALLOWED_SHOWN else ""
                text += f" (allowed: {shown}{more})"
                break
        parts.append(text or str(item))
    return "; ".join(p for p in parts if p) or None


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
        error_code: str | None = None
        sky_side = False
        api_request_id = response.headers.get("X-Request-ID")
        try:
            body = response.json()
            if isinstance(body, dict):
                api_request_id = api_request_id or body.get("request_id")
                if isinstance(body.get("error"), str):
                    error_code = body["error"]
                sky_side = details_are_sky_side(body.get("details"))
                d = body.get("detail")
                if d is not None:
                    detail = _render_details(d)
                else:
                    # The API's error envelope: {"error", "message",
                    # "details": [...], "request_id"}. The message carries
                    # the explanation and the details name the field, so the
                    # model gets both.
                    message = body.get("message")
                    rendered = _render_details(body.get("details"))
                    parts = [p for p in (message, rendered) if isinstance(p, str) and p]
                    detail = " — ".join(parts) or None
        except Exception:
            text = response.text
            if text:
                detail = text[:500]
        msg = map_http_status_to_message(
            response.status_code, detail, error_code, sky_side=sky_side
        )
        raise AsterwiseAPIError(
            msg,
            hint=msg,
            status_code=response.status_code,
            api_request_id=api_request_id if isinstance(api_request_id, str) else None,
        )

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        api_key: str,
        *,
        timeout: float,
        **kwargs: Any,
    ) -> dict[str, Any]:
        # Sent as X-Request-ID, so the API logs and tags the same id and one
        # tool call can be followed across both services.
        request_id = str(uuid.uuid4())
        start = time.perf_counter()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "asterwise-mcp/1.0",
            "Accept": "application/json",
            "X-Request-ID": request_id,
        }
        # Tell the API who is really calling, signed, so its per-IP limits
        # see the user and not this server's egress address.
        headers.update(forwarded_client_ip_headers(get_request_client_ip()))
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
                # Warning: tool_guard reports the failure to Sentry once,
                # tagged; an error here was a second, untagged event.
                logger.warning(
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
                # Warning: tool_guard reports the failure to Sentry once,
                # tagged; an error here was a second, untagged event.
                logger.warning(
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
