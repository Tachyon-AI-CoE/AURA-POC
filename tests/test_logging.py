"""Tests for the structured JSON logging module (app/logging.py)."""

from __future__ import annotations

import json
import logging

from app.logging import JsonFormatter, configure_logging, request_id_var


def test_request_id_var_default_is_none() -> None:
    token = request_id_var.set(None)
    try:
        assert request_id_var.get() is None
    finally:
        request_id_var.reset(token)


def test_json_formatter_produces_valid_json() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="aura.test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello world",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    data = json.loads(output)
    assert data["msg"] == "hello world"
    assert data["level"] == "INFO"
    assert data["name"] == "aura.test"
    assert "ts" in data


def test_json_formatter_includes_request_id_when_set() -> None:
    formatter = JsonFormatter()
    token = request_id_var.set("test-rid-123")
    try:
        record = logging.LogRecord(
            name="aura.test",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="msg with rid",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
    finally:
        request_id_var.reset(token)

    data = json.loads(output)
    assert data.get("request_id") == "test-rid-123"


def test_json_formatter_omits_request_id_when_not_set() -> None:
    formatter = JsonFormatter()
    token = request_id_var.set(None)
    try:
        record = logging.LogRecord(
            name="aura.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="no rid",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
    finally:
        request_id_var.reset(token)

    data = json.loads(output)
    assert "request_id" not in data


def test_json_formatter_surfaces_app_prefixed_extras() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="aura.test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="with extra",
        args=(),
        exc_info=None,
    )
    record.__dict__["app.scaffold_type"] = "single_agent"
    record.__dict__["app.repo_name"] = "my-agent"

    output = formatter.format(record)
    data = json.loads(output)
    assert data["app.scaffold_type"] == "single_agent"
    assert data["app.repo_name"] == "my-agent"


def test_json_formatter_includes_exception_info() -> None:
    formatter = JsonFormatter()
    try:
        raise ValueError("test error")
    except ValueError:
        import sys

        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="aura.test",
        level=logging.ERROR,
        pathname="",
        lineno=0,
        msg="something broke",
        args=(),
        exc_info=exc_info,
    )
    output = formatter.format(record)
    data = json.loads(output)
    assert "exc" in data
    assert "ValueError" in data["exc"]


def test_configure_logging_sets_level() -> None:
    configure_logging("WARNING")
    root = logging.getLogger()
    assert root.level == logging.WARNING


def test_configure_logging_installs_json_handler() -> None:
    configure_logging("INFO")
    root = logging.getLogger()
    assert any(isinstance(h.formatter, JsonFormatter) for h in root.handlers)
