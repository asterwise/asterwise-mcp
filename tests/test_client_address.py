"""Behind Cloudflare the caller is CF-Connecting-IP, but only when the
request really came from a Cloudflare edge."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

import server as srv
from client_address import caller_ip, is_cloudflare

CF_EDGE = "172.69.4.10"


@pytest.mark.parametrize("edge", [CF_EDGE, "2a06:98c0:3600::103", "::ffff:172.69.4.10"])
def test_cloudflare_edge_hands_over_the_visitor(edge):
    assert caller_ip(edge, {"cf-connecting-ip": "203.0.113.50"}) == "203.0.113.50"


def test_forged_header_from_outside_cloudflare_is_ignored():
    assert caller_ip("198.51.100.7", {"cf-connecting-ip": "203.0.113.50"}) == "198.51.100.7"


@pytest.mark.parametrize("value", ["", "x", "203.0.113.50, 1.2.3.4"])
def test_bad_header_falls_back_to_the_edge(value):
    assert caller_ip(CF_EDGE, {"cf-connecting-ip": value}) == CF_EDGE


def test_no_peer_is_none():
    assert caller_ip(None, {"cf-connecting-ip": "203.0.113.50"}) is None


@pytest.mark.parametrize(("address", "inside"), [("104.16.1.1", True), ("8.8.8.8", False), ("nope", False)])
def test_is_cloudflare(address, inside):
    assert is_cloudflare(address) is inside


async def test_the_oauth_limiter_counts_the_visitor_not_the_edge(monkeypatch):
    seen = []
    monkeypatch.setattr(srv, "_oauth_rate_allow", lambda ip: seen.append(ip) or False)
    transport = ASGITransport(app=srv.app, client=(CF_EDGE, 443))
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/token", data={"grant_type": "client_credentials"},
                         headers={"CF-Connecting-IP": "203.0.113.77"})
    assert r.status_code == 429
    assert seen == ["203.0.113.77"]
