from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from hermes_fleet.api.deps import get_ctx
from hermes_fleet.schemas.common import AuditOut
from hermes_fleet.services import audit
from hermes_fleet.services.context import Ctx

router = APIRouter(tags=["audit"])


@router.get("/audit", response_model=list[AuditOut])
def list_audit(
    ctx: Ctx = Depends(get_ctx),
    target: str | None = None,
    action: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
) -> list[AuditOut]:
    return [
        AuditOut.model_validate(a)
        for a in audit.list_audit(ctx, target=target, action=action, limit=limit)
    ]
