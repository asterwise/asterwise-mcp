"""Successful HTTP paths in AsterwiseClient."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from client import AsterwiseClient


@pytest.mark.asyncio
async def test_get_success_returns_dict() -> None:
    with patch.dict(os.environ, {"ASTERWISE_API_BASE_URL": "https://api.example.com"}):
        c = AsterwiseClient()
        await c.open()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.is_success = True
    mock_response.json.return_value = {"result": "ok"}
    mock_response.headers = {}
    mock_http = MagicMock()
    mock_http.request = AsyncMock(return_value=mock_response)
    with patch.object(c, "_client", return_value=mock_http):
        data = await c.get("/v1/ping", "key1")
    assert data == {"result": "ok"}
    await c.close()


@pytest.mark.asyncio
async def test_post_success_returns_dict() -> None:
    with patch.dict(os.environ, {"ASTERWISE_API_BASE_URL": "https://api.example.com"}):
        c = AsterwiseClient()
        await c.open()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.is_success = True
    mock_response.json.return_value = {"ok": True}
    mock_response.headers = {}
    mock_http = MagicMock()
    mock_http.request = AsyncMock(return_value=mock_response)
    with patch.object(c, "_client", return_value=mock_http):
        data = await c.post("/v1/astro/natal", "key", {"a": 1})
    assert data == {"ok": True}
    await c.close()


@pytest.mark.asyncio
async def test_post_non_dict_json_wrapped() -> None:
    with patch.dict(os.environ, {"ASTERWISE_API_BASE_URL": "https://api.example.com"}):
        c = AsterwiseClient()
        await c.open()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.is_success = True
    mock_response.json.return_value = ["a", "b"]
    mock_response.headers = {}
    mock_http = MagicMock()
    mock_http.request = AsyncMock(return_value=mock_response)
    with patch.object(c, "_client", return_value=mock_http):
        data = await c.post("/x", "k", {})
    assert data == {"data": ["a", "b"]}
    await c.close()
