"""Tools that send personal data must send it in a POST body, never a URL.

Birth dates, names, phone numbers and number plates in a query string end up
in proxy and access logs. The API's GET forms of these endpoints are
deprecated; these tools must use the POST forms, and send only what the
calculation uses.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from fastmcp import Client

import client as client_mod
from context import set_request_api_key
from server import mcp


class RecordingUpstream:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    # The app lifespan opens/closes the shared client; no-ops here.
    async def open(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def get(self, path, api_key, params=None, *, timeout=10.0):
        self.calls.append(("GET", path, dict(params or {})))
        return {"success": True, "data": {"ok": True}}

    async def post(self, path, api_key, body, *, timeout=20.0):
        self.calls.append(("POST", path, dict(body)))
        return {"success": True, "data": {"ok": True}}


async def _call(name: str, args: dict[str, Any]) -> RecordingUpstream:
    upstream = RecordingUpstream()
    client_mod._client_singleton = upstream
    set_request_api_key("aw_test_key_0123456789")
    try:
        async with Client(mcp) as c:
            result = await c.call_tool(name, args, raise_on_error=False)
        assert not result.is_error, result
    finally:
        set_request_api_key(None)
        client_mod._client_singleton = None
    return upstream


@pytest.mark.parametrize(("tool", "args", "path", "body"), [
    (
        "asterwise_get_lucky_numbers",
        {"name": "Arjun Mehta", "date": "1985-11-12"},
        "/v1/numerology/lucky-numbers",
        {"name": "Arjun Mehta", "date": "1985-11-12"},
    ),
    (
        "asterwise_get_personal_year",
        {"name": "Arjun Mehta", "date": "1985-11-12"},
        "/v1/numerology/personal-year",
        {"date": "1985-11-12", "year": datetime.now(UTC).year},
    ),
    (
        "asterwise_check_mobile_number",
        {"mobile_number": "+91 98765 43210", "name": "Arjun Mehta", "date": "1985-11-12"},
        "/v1/numerology/mobile-number",
        {"number": "+91 98765 43210"},
    ),
    (
        "asterwise_check_vehicle_number",
        {"vehicle_number": "MH01AB1234", "name": "Arjun Mehta", "date": "1985-11-12"},
        "/v1/numerology/vehicle-number",
        {"number": "MH01AB1234"},
    ),
])
async def test_tool_posts_only_what_the_calculation_uses(tool, args, path, body):
    upstream = await _call(tool, args)
    assert upstream.calls == [("POST", path, body)]


@pytest.mark.parametrize(("tool", "args"), [
    ("asterwise_get_personal_year", {"date": "1985-11-12"}),
    ("asterwise_check_mobile_number", {"mobile_number": "9876543210"}),
    ("asterwise_check_vehicle_number", {"vehicle_number": "MH01AB1234"}),
])
async def test_unused_name_and_date_are_optional(tool, args):
    upstream = await _call(tool, args)
    assert len(upstream.calls) == 1 and upstream.calls[0][0] == "POST"
