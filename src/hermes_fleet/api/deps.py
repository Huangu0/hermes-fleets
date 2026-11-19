"""FastAPI dependencies shared by routers."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from hermes_fleet.core.auth import require_api_key
from hermes_fleet.db.session import get_session
from hermes_fleet.services.context import Ctx


def get_ctx(
    request: Request,
    actor: str = Depends(require_api_key),
    session: Session = Depends(get_session),
) -> Iterator[Ctx]:
    yield Ctx(
        session=session,
        settings=request.app.state.settings,
        actor=actor,
        deps=request.app.state.deps,
    )
