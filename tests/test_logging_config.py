"""Structured logging setup."""

from __future__ import annotations

import logging

from logging_config import StructuredFormatter, configure_logging


def test_structured_formatter_outputs_json() -> None:
    fmt = StructuredFormatter()
    record = logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname="x",
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.request_id = "abc123"
    line = fmt.format(record)
    assert '"message": "hello"' in line
    assert "request_id" in line


def test_configure_logging_idempotent() -> None:
    configure_logging()
    configure_logging()
    root = logging.getLogger()
    assert root.handlers


def test_formatter_includes_exception_text() -> None:
    fmt = StructuredFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = logging.LogRecord(
            name="t",
            level=logging.ERROR,
            pathname="x",
            lineno=1,
            msg="err",
            args=(),
            exc_info=sys.exc_info(),
        )
    line = fmt.format(record)
    assert "exception" in line
    assert "boom" in line
