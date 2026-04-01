"""Tests for Asterwise HTTP client error mapping."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from client import AsterwiseClient
from errors import AsterwiseAPIError


@pytest.mark.asyncio
async def test_401_raises_api_error() -> None:
    with patch.dict(os.environ, {"ASTERWISE_API_BASE_URL": "https://api.example.com"}):
        client = AsterwiseClient()
        await client.open()
        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 401
        mock_response.json.return_value = {}
        mock_response.text = ""
        assert client._http is not None
        client._http.post = AsyncMock(return_value=mock_response)
        with pytest.raises(AsterwiseAPIError) as exc:
            await client.post("/v1/test", "bad-key", {})
        assert "Invalid API key" in str(exc.value)
        await client.close()


@pytest.mark.asyncio
async def test_429_raises_rate_limit_error() -> None:
    with patch.dict(os.environ, {"ASTERWISE_API_BASE_URL": "https://api.example.com"}):
        client = AsterwiseClient()
        await client.open()
        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 429
        mock_response.json.return_value = {}
        mock_response.text = ""
        assert client._http is not None
        client._http.post = AsyncMock(return_value=mock_response)
        with pytest.raises(AsterwiseAPIError) as exc:
            await client.post("/v1/test", "key", {})
        assert "Rate limit" in str(exc.value)
        await client.close()
