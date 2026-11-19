"""Structured (JSON-lines) logging with secret redaction."""

from __future__ import annotations

import json
import logging
import re
import sys
from typing import Any

_REDACT = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|authorization)([\"'=:\s]+)([^\s\"',}]+)"
)


def redact(text: str) -> str:
    return _REDACT.sub(lambda m: f"{m.group(1)}{m.group(2)}***", text)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": redact(record.getMessage()),
        }
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            payload.update({k: redact(str(v)) for k, v in extra.items()})
        if record.exc_info:
            payload["exc"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(json_lines: bool = True, level: int = logging.INFO) -> None:
    root = logging.getLogger("hermes_fleet")
    if getattr(root, "_fleet_configured", False):
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter() if json_lines else logging.Formatter("%(message)s"))
    root.addHandler(handler)
    root.setLevel(level)
    root._fleet_configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"hermes_fleet.{name}")
