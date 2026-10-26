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
    async def test_429_raises_retry_message(self, client: AsterwiseClient) -> None:
        await client.open()
        mock_http = MagicMock()
        mock_http.request = AsyncMock(return_value=self._mock_response(429))
        with patch.object(client, "_client", return_value=mock_http):
            with patch("client.asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(AsterwiseAPIError) as exc:
                    await client.get("/test", "key")
        assert "Rate limit reached" in str(exc.value)
        await client.close()

    def _limit_response(self, code: str, retry_after: str | None) -> MagicMock:
        r = self._mock_response(429)
        r.json.return_value = {
            "success": False,
            "error": code,
            "message": "You have reached the 500 call limit on the free Sandbox plan.",
            "retry_after": int(retry_after) if retry_after else None,
        }
        r.headers = {"Retry-After": retry_after} if retry_after else {}
        return r

    @pytest.mark.asyncio
    async def test_monthly_limit_is_not_retried_and_says_when_it_lifts(self, client: AsterwiseClient) -> None:
        await client.open()
        mock_http = MagicMock()
        mock_http.request = AsyncMock(return_value=self._limit_response("monthly_usage_limit_exceeded", None))
        with patch.object(client, "_client", return_value=mock_http):
            with patch("client.asyncio.sleep", new_callable=AsyncMock) as sleep:
                with pytest.raises(AsterwiseAPIError) as exc:
                    await client.get("/test", "key")
        assert mock_http.request.await_count == 1
        sleep.assert_not_awaited()
        text = str(exc.value)
        assert "Monthly call limit reached (monthly_usage_limit_exceeded)" in text
        assert "1st of next month at 00:00 UTC" in text
        assert "500 call limit on the free Sandbox plan" in text
        assert exc.value.error_code == "monthly_usage_limit_exceeded"
        await client.close()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("code", "phrase"),
        [("burst_limit_exceeded", "Per-minute limit reached"), ("ip_rate_limit_exceeded", "Per-network limit reached")],
    )
    async def test_minute_limits_retry_then_name_the_limit_and_wait(
        self, client: AsterwiseClient, code: str, phrase: str
    ) -> None:
        await client.open()
        mock_http = MagicMock()
        mock_http.request = AsyncMock(return_value=self._limit_response(code, "60"))
        with patch.object(client, "_client", return_value=mock_http):
            with patch("client.asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(AsterwiseAPIError) as exc:
                    await client.get("/test", "key")
        assert mock_http.request.await_count == 4  # unchanged: the first try and three retries
        text = str(exc.value)
        assert f"{phrase} ({code})" in text
        assert "Wait 60 seconds" in text
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
