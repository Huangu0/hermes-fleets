"""ORM models. Every table change ships with an Alembic migration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from hermes_fleet.db.base import Base, utcnow


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64), index=True)
    target: Mapped[str] = mapped_column(String(255), index=True)
    outcome: Mapped[str] = mapped_column(String(16), default="ok")
    summary: Mapped[dict[str, Any]] = mapped_column(default=dict)
