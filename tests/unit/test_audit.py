from __future__ import annotations

from typing import Any

import pytest

from hermes_fleet.core.config import Settings
from hermes_fleet.db.base import make_engine, make_session_factory
from hermes_fleet.db.migrate import upgrade
from hermes_fleet.services import audit
from hermes_fleet.services.context import Ctx


@audit.audited("thing.create", target=lambda name, **_: f"thing:{name}", summary=lambda r: r)
def create_thing(ctx: Ctx, name: str, fail: bool = False) -> dict[str, Any]:
    if fail:
        raise ValueError("boom")
    return {"created": name, "token": "abc123"}


def test_audited_records_actor_target_summary(settings: Settings) -> None:
    upgrade(settings.db_url)
    f = make_session_factory(make_engine(settings.db_url))
    with f() as s:
        ctx = Ctx(session=s, settings=settings, actor="alice")
        create_thing(ctx, "x")
        s.commit()
        with pytest.raises(ValueError):
            create_thing(ctx, "y", fail=True)
        rows = audit.list_audit(ctx)
    assert [r.outcome for r in rows] == ["error", "ok"]
    ok = rows[1]
    assert ok.actor == "alice" and ok.target == "thing:x" and ok.summary["created"] == "x"
    assert rows[0].summary["error"] == "ValueError"
