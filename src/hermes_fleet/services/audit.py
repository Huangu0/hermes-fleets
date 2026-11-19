"""Audit log: a service-layer decorator records every write use case."""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from sqlalchemy import select

from hermes_fleet.core.logging import redact
from hermes_fleet.db.models import AuditLog
from hermes_fleet.services.context import Ctx

P = ParamSpec("P")
R = TypeVar("R")

_MAX_SUMMARY = 4000


def _clip(value: Any) -> Any:
    text = redact(repr(value))
    return value if len(text) <= _MAX_SUMMARY else text[:_MAX_SUMMARY] + "..."


def record(
    ctx: Ctx, action: str, target: str, summary: dict[str, Any], outcome: str = "ok"
) -> None:
    ctx.session.add(
        AuditLog(
            actor=ctx.actor,
            action=action,
            target=target[:255],
            outcome=outcome,
            summary={k: _clip(v) for k, v in summary.items()},
        )
    )
    ctx.session.flush()


def audited(
    action: str,
    target: Callable[..., str],
    summary: Callable[[Any], dict[str, Any]] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorate ``fn(ctx, ...)``: on success write an audit row; on failure write
    an ``error`` row in a separate transaction-independent way (best effort)."""

    def deco(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            ctx = args[0]
            assert isinstance(ctx, Ctx)
            tgt = target(*args[1:], **kwargs)
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:
                ctx.session.rollback()
                record(ctx, action, tgt, {"error": type(exc).__name__, "detail": str(exc)}, "error")
                ctx.session.commit()
                raise
            record(ctx, action, tgt, summary(result) if summary else {})
            return result

        return wrapper

    return deco


def list_audit(
    ctx: Ctx, *, target: str | None = None, action: str | None = None, limit: int = 100
) -> list[AuditLog]:
    q = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    if target:
        q = q.where(AuditLog.target == target)
    if action:
        q = q.where(AuditLog.action == action)
    return list(ctx.session.scalars(q))
