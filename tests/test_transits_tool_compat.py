"""asterwise_get_transits needs no birth data, but older clients still send it.

The tool dropped its required birth object on 2026-10-22 (MCP #36). Clients
holding the old schema keep sending birth, and birth.ayanamsa was how they
picked the zodiac, so the tool must accept it and honour it.
"""
from __future__ import annotations

from typing import Any

import pytest
from fastmcp import Client

import client as client_mod
from context import set_request_api_key
from server import mcp


class RecordingUpstream:
    def __init__(self) -> None:
        self.bodies: list[dict[str, Any]] = []

    async def open(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def post(self, path, api_key, body, *, timeout=20.0):
        assert path == "/v1/astro/transits"
        self.bodies.append(dict(body))
        return {"success": True, "data": {"ingresses": [], "stations": []}}


async def _body(args: dict[str, Any]) -> dict[str, Any]:
    upstream = RecordingUpstream()
    client_mod._client_singleton = upstream
    set_request_api_key("aw_test_key_0123456789")
    try:
        async with Client(mcp) as c:
            result = await c.call_tool("asterwise_get_transits", args, raise_on_error=False)
        assert not result.is_error, result
    finally:
        set_request_api_key(None)
        client_mod._client_singleton = None
    return upstream.bodies[0]


_DATES = {"from_date": "2026-03-01", "to_date": "2026-03-31"}
_BIRTH = {"date": "1990-05-15", "lat": 28.6139, "lon": 77.209}


@pytest.mark.asyncio
@pytest.mark.parametrize(("extra", "zodiac"), [
    ({}, "lahiri"),
    ({"ayanamsa": "tropical"}, "tropical"),
    ({"birth": _BIRTH}, "lahiri"),
    ({"birth": {**_BIRTH, "ayanamsa": "tropical"}}, "tropical"),
    ({"birth": {**_BIRTH, "ayanamsa": "tropical"}, "ayanamsa": "kp"}, "kp"),
])
async def test_body_has_only_dates_and_zodiac(extra, zodiac):
    body = await _body({**_DATES, **extra})
    assert body == {**_DATES, "ayanamsa": zodiac}
