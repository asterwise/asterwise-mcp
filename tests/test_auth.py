"""Auth: JWT hash cache, extraction, eviction."""

from __future__ import annotations

import base64
import json
import os
import time
from unittest.mock import patch

import jwt as pyjwt
import pytest

from auth import (
    TOKEN_TTL,
    TokenExpiredError,
    TokenInvalidError,
    _evict_expired_tokens,
    _hash_key,
    _token_cache,
    create_token,
    decode_token,
    extract_api_key,
    validate_and_get_key,
)
from errors import AuthError


@pytest.fixture(autouse=True)
def clear_token_cache() -> None:
    _token_cache.clear()
    yield
    _token_cache.clear()


class TestTokenCreation:
    def test_create_token_returns_string(self) -> None:
        token = create_token("test-key-abc123")
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_token_does_not_contain_raw_key(self) -> None:
        api_key = "my-secret-api-key-xyz"
        token = create_token(api_key)
        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        payload_b64 += "=" * (padding % 4)
        payload = json.loads(base64.b64decode(payload_b64))
        assert api_key not in json.dumps(payload)
        assert api_key not in payload.get("sub", "")

    def test_token_sub_is_hash_not_key(self) -> None:
        api_key = "test-api-key"
        token = create_token(api_key)
        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        payload_b64 += "=" * (padding % 4)
        payload = json.loads(base64.b64decode(payload_b64))
        assert payload["sub"] == _hash_key(api_key)
        assert payload["iss"] == "asterwise-mcp"

    def test_token_stored_in_cache(self) -> None:
        api_key = "cached-key-test"
        _token_cache.clear()
        create_token(api_key)
        assert _hash_key(api_key) in _token_cache

    def test_missing_jwt_secret_raises(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="JWT_SECRET"):
                create_token("any-key")

    def test_short_jwt_secret_raises(self) -> None:
        with patch.dict(os.environ, {"JWT_SECRET": "tooshort"}):
            with pytest.raises(RuntimeError, match="32 characters"):
                create_token("any-key")


class TestTokenDecoding:
    def test_roundtrip_returns_original_key(self) -> None:
        api_key = "roundtrip-test-key-12345"
        token = create_token(api_key)
        recovered = decode_token(token)
        assert recovered == api_key

    def test_expired_cache_raises_expired_error(self) -> None:
        api_key = "expiry-test-key"
        token = create_token(api_key)
        key_hash = _hash_key(api_key)
        # decode_token calls _evict_expired_tokens first; skip eviction so we can
        # simulate a stale cache row after JWT verification.
        with patch("auth._evict_expired_tokens"):
            _token_cache[key_hash] = (api_key, time.time() - 1)
            with pytest.raises(TokenExpiredError):
                decode_token(token)

    def test_tampered_token_raises_invalid(self) -> None:
        with pytest.raises(TokenInvalidError):
            decode_token("not.a.valid.jwt")

    def test_unknown_hash_raises_invalid(self) -> None:
        payload = {
            "sub": "unknownhash123",
            "iat": int(time.time()),
            "exp": int(time.time()) + TOKEN_TTL,
            "iss": "asterwise-mcp",
        }
        fake_token = pyjwt.encode(
            payload,
            os.environ["JWT_SECRET"],
            algorithm="HS256",
        )
        _token_cache.clear()
        with pytest.raises(TokenInvalidError, match="not recognized"):
            decode_token(fake_token)

    def test_wrong_issuer_raises_invalid(self) -> None:
        payload = {
            "sub": "somehash",
            "iat": int(time.time()),
            "exp": int(time.time()) + TOKEN_TTL,
            "iss": "some-other-server",
        }
        token = pyjwt.encode(
            payload,
            os.environ["JWT_SECRET"],
            algorithm="HS256",
        )
        with pytest.raises(TokenInvalidError):
            decode_token(token)


class TestKeyExtraction:
    def test_bearer_token_extracts_key(self) -> None:
        api_key = "bearer-test-key-abc"
        token = create_token(api_key)
        headers = {"authorization": f"Bearer {token}"}
        result = extract_api_key(headers)
        assert result == api_key

    def test_x_api_key_header_works(self) -> None:
        headers = {"x-api-key": "direct-api-key"}
        result = extract_api_key(headers)
        assert result == "direct-api-key"

    def test_bearer_takes_priority_over_api_key(self) -> None:
        api_key = "priority-test-key"
        token = create_token(api_key)
        headers = {
            "authorization": f"Bearer {token}",
            "x-api-key": "should-be-ignored",
        }
        result = extract_api_key(headers)
        assert result == api_key

    def test_missing_auth_returns_none(self) -> None:
        result = extract_api_key({})
        assert result is None

    def test_validate_and_get_key_raises_on_missing(self) -> None:
        with pytest.raises(AuthError, match="No API key"):
            validate_and_get_key({})


class TestCacheEviction:
    def test_evict_removes_expired_entries(self) -> None:
        _token_cache["expired_hash"] = ("some-key", time.time() - 1)
        _token_cache["valid_hash"] = ("other-key", time.time() + 3600)
        _evict_expired_tokens()
        assert "expired_hash" not in _token_cache
        assert "valid_hash" in _token_cache
