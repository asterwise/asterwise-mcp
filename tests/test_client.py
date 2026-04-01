"""HTTP client: safe_segment, error mapping."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from client import AsterwiseClient, safe_segment
from errors import AsterwiseAPIError


class TestSafeSegment:
    def test_normal_string_unchanged(self) -> None:
        assert safe_segment("libra") == "libra"

    def test_spaces_encoded(self) -> None:
        result = safe_segment("libra scorpio")
        assert " " not in result
        assert "%20" in result

    def test_slashes_encoded(self) -> None:
        result = safe_segment("2026/01/01")
        assert "/" not in result

    def test_special_chars_encoded(self) -> None:
        result = safe_segment("test&value=1")
        assert "&" not in result
        assert "=" not in result

    def test_numbers_as_string(self) -> None:
        assert safe_segment(str(7)) == "7"

    def test_empty_string(self) -> None:
        assert safe_segment("") == ""


class TestClientErrorMapping:
    @pytest.fixture
    def client(self) -> AsterwiseClient:
        with patch.dict(os.environ, {"ASTERWISE_API_BASE_URL": "https://api.example.com"}):
            c = AsterwiseClient()
            return c

    def _mock_response(self, status_code: int) -> MagicMock:
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.is_success = status_code < 400
        mock_response.json.return_value = {}
        mock_response.text = ""
        mock_response.headers = {}
        return mock_response

    @pytest.mark.asyncio
    async def test_401_raises_with_dashboard_link(self, client: AsterwiseClient) -> None:
        await client.open()
        mock_http = MagicMock()
        mock_http.request = AsyncMock(return_value=self._mock_response(401))
        with patch.object(client, "_client", return_value=mock_http):
            with patch("client.asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(AsterwiseAPIError) as exc:
                    await client.get("/test", "bad-key")
        assert "asterwise.com/dashboard" in str(exc.value)
        await client.close()

    @pytest.mark.asyncio
    async def test_429_raises_with_pricing_link(self, client: AsterwiseClient) -> None:
        await client.open()
        mock_http = MagicMock()
        mock_http.request = AsyncMock(return_value=self._mock_response(429))
        with patch.object(client, "_client", return_value=mock_http):
            with patch("client.asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(AsterwiseAPIError) as exc:
                    await client.get("/test", "key")
        assert "asterwise.com/pricing" in str(exc.value)
        await client.close()

    @pytest.mark.asyncio
    async def test_5xx_raises_with_status_link(self, client: AsterwiseClient) -> None:
        await client.open()
        mock_http = MagicMock()
        mock_http.request = AsyncMock(return_value=self._mock_response(500))
        with patch.object(client, "_client", return_value=mock_http):
            with patch("client.asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(AsterwiseAPIError) as exc:
                    await client.post("/test", "key", {})
        assert "status.asterwise.com" in str(exc.value)
        await client.close()
