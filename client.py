"""Shared async httpx client for the Asterwise REST API."""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any
from urllib.parse import quote

import httpx

from errors import AsterwiseAPIError, map_http_status_to_message

logger = logging.getLogger("asterwise_mcp")


def _safe_path_segment(value: str) -> str:
    """URL-encode a single path segment."""
    return quote(str(value), safe="")


class AsterwiseClient:
    """Single shared async client — use `get_client()` from the app lifespan."""

    def __init__(self) -> None:
        raw = os.getenv("ASTERWISE_API_BASE_URL")
        if not raw:
            raise RuntimeError(
                "ASTERWISE_API_BASE_URL is not set. Configure the Asterwise API base URL "
                "in the environment (e.g. https://api.asterwise.com)."
            )
        self.base_url = raw.rstrip("/")
        self.timeout = 30.0
        self._http: httpx.AsyncClient | None = None

    async def open(self) -> None:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"User-Agent": "asterwise-mcp/1.0"},
            )

    async def close(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            raise RuntimeError("AsterwiseClient is not initialized; check app lifespan.")
        return self._http

    def _raise_for_status(
        self, response: httpx.Response, default_detail: str | None = None
    ) -> None:
        if response.is_success:
            return
        detail = default_detail
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

    async def post(self, path: str, api_key: str, body: dict[str, Any]) -> dict[str, Any]:
        """POST JSON to Asterwise API with auth."""
        request_id = str(uuid.uuid4())[:8]
        logger.info(
            "upstream_request",
            extra={
                "request_id": request_id,
                "method": "POST",
                "path": path,
            },
        )
        try:
            r = await self._client().post(
                path,
                json=body,
                headers={"X-API-Key": api_key},
            )
            logger.info(
                "upstream_response",
                extra={
                    "request_id": request_id,
                    "status": r.status_code,
                    "path": path,
                },
            )
            self._raise_for_status(r)
            data = r.json()
            if not isinstance(data, dict):
                return {"data": data}
            return data
        except AsterwiseAPIError:
            raise
        except Exception as e:
            logger.error(
                "upstream_error",
                extra={
                    "request_id": request_id,
                    "path": path,
                    "error": str(e),
                },
            )
            raise

    async def get(
        self, path: str, api_key: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """GET from Asterwise API with auth."""
        request_id = str(uuid.uuid4())[:8]
        logger.info(
            "upstream_request",
            extra={
                "request_id": request_id,
                "method": "GET",
                "path": path,
            },
        )
        try:
            r = await self._client().get(
                path,
                params=params or {},
                headers={"X-API-Key": api_key},
            )
            logger.info(
                "upstream_response",
                extra={
                    "request_id": request_id,
                    "status": r.status_code,
                    "path": path,
                },
            )
            self._raise_for_status(r)
            data = r.json()
            if not isinstance(data, dict):
                return {"data": data}
            return data
        except AsterwiseAPIError:
            raise
        except Exception as e:
            logger.error(
                "upstream_error",
                extra={
                    "request_id": request_id,
                    "path": path,
                    "error": str(e),
                },
            )
            raise


_client_singleton: AsterwiseClient | None = None


def get_client() -> AsterwiseClient:
    """Return the process-wide Asterwise HTTP client."""
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = AsterwiseClient()
    return _client_singleton
