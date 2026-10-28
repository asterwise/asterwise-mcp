"""Both daily-factors tools pass target_time through (Release 5, 2026-10-27).

The API reads the day's sky at target_time (HH:MM, default 12:00 local). The
tools send it only when given, so the API default applies otherwise, and a
malformed time is refused before any upstream call.
"""
from __future__ import annotations

from typing import Any

import pytest
from fastmcp import Client

import client as client_mod
from context import set_request_api_key
from server import mcp

BIRTH = {"date": "1990-06-15", "time": "14:30", "lat": 19.076, "lon": 72.8777, "timezone": "Asia/Kolkata"}
TOOLS = {
    "asterwise_get_vedic_daily_factors": "/v1/astro/daily-factors",
    "asterwise_get_western_daily_factors": "/v1/western/daily-factors",
}


class RecordingUpstream:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def open(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def post(self, path, api_key, body, *, timeout=20.0):
        self.calls.append((path, dict(body)))
        return {"success": True, "data": {"factors": []}}


async def _call(tool: str, args: dict[str, Any]):
    upstream = RecordingUpstream()
    client_mod._client_singleton = upstream
    set_request_api_key("aw_test_key_0123456789")
    try:
        async with Client(mcp) as c:
            result = await c.call_tool(tool, {"birth": BIRTH, **args}, raise_on_error=False)
    finally:
        set_request_api_key(None)
        client_mod._client_singleton = None
    return result, upstream.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", sorted(TOOLS))
async def test_target_time_is_sent_only_when_given(tool):
    _, with_time = await _call(tool, {"target_date": "2026-10-12", "target_time": "07:30"})
    _, without = await _call(tool, {"target_date": "2026-10-12"})

    assert with_time[0][0] == TOOLS[tool]
    assert with_time[0][1]["target_time"] == "07:30"
    assert "target_time" not in without[0][1]


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", sorted(TOOLS))
@pytest.mark.parametrize("bad", ["24:00", "7:30", "07:60", "noon", "1٢:30", "07:3٣"])
async def test_a_malformed_time_is_refused_before_the_api(tool, bad):
    result, calls = await _call(tool, {"target_time": bad})

    assert result.is_error and calls == []
