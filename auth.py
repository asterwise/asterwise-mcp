"""JWT + server-side cache: Bearer tokens never embed the raw API key."""

from __future__ import annotations

import hashlib
import logging
import os
import time
from collections.abc import Mapping
from typing import Any, Optional

import jwt

from errors import AuthError, TokenExpiredError, TokenInvalidError

logger = logging.getLogger("asterwise_mcp.auth")

JWT_ALGORITHM = "HS256"
TOKEN_TTL = 3600
ISSUER = "asterwise-mcp"

# Server-side token cache: {key_hash: (api_key, expires_at)}
_token_cache: dict[str, tuple[str, float]] = {}


def _get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET environment variable is not set. Cannot issue or verify tokens."
        )
    if len(secret) < 32:
        raise RuntimeError(
            "JWT_SECRET must be at least 32 characters. Generate one with: "
            "python3 -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return secret


def _hash_key(api_key: str) -> str:
    """One-way hash of API key. Never reversible."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def _evict_expired_tokens() -> None:
    """Remove expired entries to prevent unbounded cache growth."""
    now = time.time()
    expired = [h for h, (_, exp) in _token_cache.items() if now > exp]
    for h in expired:
        _token_cache.pop(h, None)
    if expired:
        logger.debug(
            "token_cache_eviction",
            extra={"evicted": len(expired), "remaining": len(_token_cache)},
        )


def create_token(api_key: str) -> str:
    """
    Create a signed JWT. Payload contains only a hash of the API key.
    The real key lives in _token_cache only.
    """
    _evict_expired_tokens()
    key_hash = _hash_key(api_key)
    now = time.time()
    expires_at = now + TOKEN_TTL
    _token_cache[key_hash] = (api_key, expires_at)
    payload: dict[str, Any] = {
        "sub": key_hash,
        "iat": int(now),
        "exp": int(expires_at),
        "iss": ISSUER,
    }
    token = jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)
    logger.info(
        "token_issued",
        extra={
            "key_hash_prefix": key_hash[:8],
            "expires_in": TOKEN_TTL,
        },
    )
    return token


def decode_token(token: str) -> str:
    """Validate JWT and return the API key from the server cache."""
    _evict_expired_tokens()
    try:
        payload = jwt.decode(
            token,
            _get_jwt_secret(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat", "iss"]},
            issuer=ISSUER,
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError(
            "Token has expired. Request a new one via POST /oauth/token"
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalidError(
            f"Invalid token: {exc}. Request a new one via POST /oauth/token"
        ) from exc

    key_hash = payload.get("sub")
    issuer = payload.get("iss")
    if issuer != ISSUER:
        raise TokenInvalidError("Token was not issued by this server")

    if not isinstance(key_hash, str) or not key_hash.strip():
        raise TokenInvalidError(
            "Invalid token structure. Request a new one via POST /oauth/token"
        )

    cached = _token_cache.get(key_hash)
    if not cached:
        raise TokenInvalidError(
            "Token not recognized or was revoked. Request a new one via POST /oauth/token"
        )

    api_key, expires_at = cached
    if time.time() > expires_at:
        _token_cache.pop(key_hash, None)
        raise TokenExpiredError("Token has expired. Request a new one via POST /oauth/token")

    return api_key


def _lower_headers(headers: Mapping[str, str] | dict[str, str]) -> dict[str, str]:
    return {str(k).lower(): v for k, v in headers.items()}


def extract_api_key(headers: Mapping[str, str] | dict[str, str]) -> Optional[str]:
    """
    Extract API key from normalized headers (Bearer first, then X-API-Key).
    Returns None if neither is present. Does not raise for missing auth.
    """
    h = _lower_headers(headers)
    auth_header = h.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if token:
            try:
                return decode_token(token)
            except (TokenExpiredError, TokenInvalidError):
                raise
    api_key = h.get("x-api-key", "").strip()
    if api_key:
        return api_key
    return None


def validate_and_get_key(headers: Mapping[str, str] | dict[str, str]) -> str:
    """Return the API key or raise AuthError."""
    result = extract_api_key(headers)
    if not result:
        raise AuthError(
            "No API key provided. Pass X-API-Key header "
            "or Authorization: Bearer <token>. "
            "Get a free key at asterwise.com/dashboard"
        )
    return result
