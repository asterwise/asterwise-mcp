"""Tests for JWT + cache auth (no raw API key in token payload)."""

from __future__ import annotations

import base64
import json
import time
from unittest.mock import patch

import pytest

from auth import TokenExpiredError, TokenInvalidError, _hash_key, _key_cache, create_token, decode_token


@pytest.fixture(autouse=True)
def clear_key_cache() -> None:
    _key_cache.clear()
    yield
    _key_cache.clear()


def test_create_and_decode_token() -> None:
    """Token round-trip returns original API key."""
    with patch.dict("os.environ", {"JWT_SECRET": "test-secret-32chars-padding-ok"}):
        api_key = "test-api-key-12345"
        token = create_token(api_key)
        assert isinstance(token, str)
        recovered = decode_token(token)
        assert recovered == api_key


def test_token_does_not_contain_api_key() -> None:
    """JWT payload must not expose the raw API key."""
    with patch.dict("os.environ", {"JWT_SECRET": "test-secret-32chars-padding-ok"}):
        api_key = "super-secret-key-abc123"
        token = create_token(api_key)
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.b64decode(payload_b64))
        assert api_key not in str(payload)
        assert api_key not in payload.get("sub", "")


def test_expired_token_raises() -> None:
    """Expired cache entry must be rejected with TokenExpiredError."""
    with patch.dict("os.environ", {"JWT_SECRET": "test-secret-32chars-padding-ok"}):
        api_key = "expiring-key"
        token = create_token(api_key)
        key_hash = _hash_key(api_key)
        _key_cache[key_hash] = (api_key, time.time() - 1)
        with pytest.raises(TokenExpiredError):
            decode_token(token)


def test_invalid_token_raises() -> None:
    """Tampered tokens must be rejected."""
    with patch.dict("os.environ", {"JWT_SECRET": "test-secret-32chars-padding-ok"}):
        with pytest.raises(TokenInvalidError):
            decode_token("not.a.valid.jwt.token")
