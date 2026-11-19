from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AuditOut(ORMModel):
    id: int
    ts: datetime
    actor: str
    action: str
    target: str
    outcome: str
    summary: dict[str, Any]


class Problem(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    code: str
    instance: str
