"""The caller's address, behind Cloudflare.

mcp.asterwise.com is proxied by Cloudflare, so the address the platform
proxy reports (uvicorn --forwarded-allow-ips) is a Cloudflare edge server,
shared by every visitor routed through it. When that address is inside
Cloudflare's published ranges, the caller is Cloudflare's own
``CF-Connecting-IP`` header; a request arriving any other way comes from
outside those ranges, so a forged header is ignored. Same rule as
asterwise-api app/shared/client_ip.py, which receives this address signed.
"""

from __future__ import annotations

import ipaddress
from collections.abc import Mapping

# https://www.cloudflare.com/ips/ (fetched 2026-10-05).
CLOUDFLARE_RANGES = tuple(ipaddress.ip_network(n) for n in (
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20",
    "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
    "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32", "2405:b500::/32",
    "2405:8100::/32", "2a06:98c0::/29", "2c0f:f248::/32",
))


def _ip(value: str):
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return None
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip


def is_cloudflare(address: str) -> bool:
    ip = _ip(address)
    return ip is not None and any(ip in network for network in CLOUDFLARE_RANGES)


def caller_ip(peer: str | None, headers: Mapping[str, str]) -> str | None:
    """The visitor's address given the transport peer and request headers."""
    if peer and is_cloudflare(peer):
        visitor = (headers.get("cf-connecting-ip") or "").strip()
        if _ip(visitor) is not None:
            return visitor
    return peer or None
