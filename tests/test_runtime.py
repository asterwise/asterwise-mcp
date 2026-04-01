"""MCP tool_error / invalid_params helpers."""

from __future__ import annotations

import pytest
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS
from pydantic import BaseModel, ValidationError

from runtime import invalid_params, raise_validation_error, tool_error


class TestToolError:
    def test_tool_error_raises_mcp_error(self) -> None:
        with pytest.raises(McpError) as exc:
            tool_error("Something went wrong")
        assert exc.value.error.code == INTERNAL_ERROR
        assert "Something went wrong" in exc.value.error.message

    def test_tool_error_never_returns(self) -> None:
        with pytest.raises(McpError):
            tool_error("error")

    def test_invalid_params_raises_mcp_error(self) -> None:
        with pytest.raises(McpError) as exc:
            invalid_params("Bad date format")
        assert exc.value.error.code == INVALID_PARAMS
        assert "Bad date format" in exc.value.error.message


def test_raise_validation_error_maps_pydantic() -> None:
    class Tiny(BaseModel):
        n: int

    with pytest.raises(McpError) as exc:
        try:
            Tiny.model_validate({"n": "x"})
        except ValidationError as e:
            raise_validation_error(e)
    assert exc.value.error.code == INVALID_PARAMS
    assert "n" in exc.value.error.message
