"""Centralized error types and HTTP error mapping for the Asterwise MCP proxy."""

from __future__ import annotations


class AsterwiseMCPError(Exception):
    """Base error for this server."""

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.hint = hint


class AuthError(AsterwiseMCPError):
    """Missing or invalid authentication."""

    pass


class TokenExpiredError(AuthError):
    """JWT access token has expired."""

    pass


class TokenInvalidError(AuthError):
    """JWT is malformed or signature invalid."""

    pass


class AsterwiseAPIError(AsterwiseMCPError):
    """Upstream Asterwise API returned an error."""

    pass


def map_http_status_to_message(status_code: int, detail: str | None) -> str:
    """Map HTTP status codes to actionable messages for LLM clients."""
    if status_code == 401:
        return (
            "Invalid API key. Get one free at https://asterwise.com/dashboard. "
            "Send a valid key via the X-API-Key header or a Bearer token from POST /oauth/token."
        )
    if status_code == 422:
        extra = f" Details: {detail}" if detail else ""
        return (
            "Invalid parameters — the Asterwise API rejected the request body or query."
            f"{extra} "
            "Fix the field mentioned in the error (check date format YYYY-MM-DD, time HH:MM, "
            "latitude/longitude ranges, and enum values) and retry."
        )
    if status_code == 429:
        return (
            "Rate limit exceeded. Upgrade at https://asterwise.com/pricing or retry after a short wait."
        )
    if status_code >= 500:
        return (
            "Asterwise API error. Check status at https://status.asterwise.com and retry later."
        )
    if detail:
        return f"Asterwise API request failed (HTTP {status_code}): {detail}"
    return f"Asterwise API request failed with HTTP {status_code}."
