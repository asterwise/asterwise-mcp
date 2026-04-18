"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import asyncio
import os

import pytest

os.environ.setdefault("ASTERWISE_API_BASE_URL", "https://api.asterwise.com")
os.environ.setdefault("JWT_SECRET", "test-secret-that-is-long-enough-32chars")
os.environ.setdefault("MCP_SERVER_PORT", "8001")
os.environ.setdefault("MCP_SERVER_HOST", "127.0.0.1")
# Isolate OAuth proxy tests from local .env / shell (test_oauth_mcp expects asterwise.com).
os.environ["FRONTEND_URL"] = "https://asterwise.com"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
