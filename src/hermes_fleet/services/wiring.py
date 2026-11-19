"""Builds the adapter/service dependency map injected into every Ctx."""

from __future__ import annotations

from typing import Any

from hermes_fleet.core.config import Settings


def build_deps(settings: Settings, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    deps: dict[str, Any] = {}
    deps.update(overrides or {})
    return deps
