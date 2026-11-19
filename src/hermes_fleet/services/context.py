"""Service context: everything a use case needs, passed explicitly (actor included)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from hermes_fleet.core.config import Settings


@dataclass
class Ctx:
    session: Session
    settings: Settings
    actor: str = "system"
    # Late-bound adapters/services (hermes adapter, OV client, hooks...).
    deps: dict[str, Any] = field(default_factory=dict)

    def dep(self, name: str) -> Any:
        try:
            return self.deps[name]
        except KeyError as exc:  # pragma: no cover - wiring bug
            raise RuntimeError(f"dependency {name!r} not wired") from exc
