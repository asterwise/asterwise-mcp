"""Tool inputs promise only what the API does (Grok findings, 2026-10-06).

* 15 tools call endpoints that reject a request without a birth time; their
  `time` is required here instead of failing upstream as INTERNAL_ERROR.
* asterwise_get_kp_significators filters to house_number itself: the API has
  no house filter and returned all twelve houses.
* asterwise_get_business_name_analysis no longer needs a birth date the API
  never used, and sends the name in a POST body, not the URL.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

import client as client_mod
from context import set_request_api_key
from fastmcp import Client
from server import mcp

TIME_REQUIRED = {
    "asterwise_get_char_dasha", "asterwise_get_crystal_recommendations_natal",
    "asterwise_get_dasha_transits", "asterwise_get_gemstone_recommendations",
    "asterwise_get_ghat_chakra", "asterwise_get_gochar", "asterwise_get_kp_chart",
    "asterwise_get_kp_significators", "asterwise_get_nakshatra_prediction",
    "asterwise_get_pitra_dosha", "asterwise_get_remedies", "asterwise_get_special_ascendants",
    "asterwise_get_varshaphal", "asterwise_get_varshaphal_harsha_bala",
    "asterwise_get_varshaphal_saham",
}
BIRTH = {"date": "1990-06-15", "time": "14:30", "lat": 19.076, "lon": 72.8777, "timezone": "Asia/Kolkata"}


def _tools() -> dict[str, dict[str, Any]]:
    async def _load():
        async with Client(mcp) as c:
            return {t.name: t.inputSchema for t in await c.list_tools()}
    return asyncio.run(_load())


def _birth_schema(schema: dict[str, Any]) -> dict[str, Any] | None:
    birth = schema.get("properties", {}).get("birth")
    if birth and "$ref" in birth:
        birth = schema.get("$defs", {}).get(birth["$ref"].rsplit("/", 1)[-1])
    return birth if birth and "date" in birth.get("properties", {}) else None


def test_time_is_required_exactly_on_the_tools_whose_endpoint_needs_it():
    from models import BirthData, TimedBirthData

    vedic = {BirthData.__doc__.strip(), TimedBirthData.__doc__.strip()}
    with_birth = {
        name: b for name, s in _tools().items()
        if (b := _birth_schema(s)) and b.get("description", "").strip() in vedic
    }
    assert len(with_birth) > len(TIME_REQUIRED)  # the time-optional tools are in view too
    required = {name for name, b in with_birth.items() if "time" in b.get("required", [])}
    assert required == TIME_REQUIRED
    for name in TIME_REQUIRED:
        assert "no sunrise" in with_birth[name]["properties"]["time"]["description"]


class _Upstream:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.calls: list[tuple[str, str, Any]] = []

    async def open(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def get(self, path, api_key, params=None, *, timeout=10.0):
        self.calls.append(("GET", path, params))
        return json.loads(json.dumps(self.data))

    async def post(self, path, api_key, body, *, timeout=20.0):
        self.calls.append(("POST", path, body))
        return json.loads(json.dumps(self.data))


def _call(name: str, args: dict[str, Any], upstream: _Upstream):
    async def _run():
        client_mod._client_singleton = upstream
        set_request_api_key("aw_test_key_0123456789")
        try:
            async with Client(mcp) as c:
                return await c.call_tool(name, args, raise_on_error=False)
        finally:
            set_request_api_key(None)
            client_mod._client_singleton = None
    return asyncio.run(_run())


SIGNIFICATORS = {
    "success": True,
    "data": {
        "ayanamsa": "kp",
        "significators": {str(h): {"house": h, "sign_lord": "Mars"} for h in range(1, 13)},
        "planet_significators": {"Sun": {"all_significators": [1, 5]}},
    },
}


def test_kp_significators_returns_only_the_requested_house():
    upstream = _Upstream(SIGNIFICATORS)
    result = _call("asterwise_get_kp_significators",
                   {"birth": BIRTH, "house_number": 7, "response_format": "json"}, upstream)
    assert not result.is_error
    data = json.loads(result.content[0].text)["data"]
    assert list(data["significators"]) == ["7"]
    assert data["planet_significators"] == {"Sun": {"all_significators": [1, 5]}}
    assert "house_number" not in upstream.calls[0][2]


def test_kp_significators_without_a_house_returns_all_twelve():
    result = _call("asterwise_get_kp_significators", {"birth": BIRTH, "response_format": "json"},
                   _Upstream(SIGNIFICATORS))
    assert len(json.loads(result.content[0].text)["data"]["significators"]) == 12


def test_kp_significators_refuses_a_house_outside_1_to_12_before_calling_the_api():
    upstream = _Upstream(SIGNIFICATORS)
    result = _call("asterwise_get_kp_significators", {"birth": BIRTH, "house_number": 13}, upstream)
    assert result.is_error and "between 1 and 12" in result.content[0].text
    assert upstream.calls == []


def test_business_name_needs_no_date_and_sends_the_name_in_the_body():
    upstream = _Upstream({"success": True, "data": {"input": "Asterwise Labs"}})
    result = _call("asterwise_get_business_name_analysis", {"business_name": "Asterwise Labs"}, upstream)
    assert not result.is_error
    assert upstream.calls == [("POST", "/v1/numerology/business-name", {"name": "Asterwise Labs"})]
    # Older calls that still pass a date keep working.
    again = _call("asterwise_get_business_name_analysis",
                  {"business_name": "Asterwise Labs", "date": "1990-06-15"}, upstream)
    assert not again.is_error
    assert upstream.calls[-1][2] == {"name": "Asterwise Labs"}
