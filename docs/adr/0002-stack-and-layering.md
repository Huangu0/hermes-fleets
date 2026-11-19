# ADR-0002 · Stack and layering

- Status: accepted (stage 0)

## Decision
- Python 3.12 service venv managed by `uv`; FastAPI + Pydantic v2 + pydantic-settings; SQLAlchemy 2 +
  Alembic; SQLite in development with `journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`
  set on every connection.
- Layering `api → services → domain/repos → adapters`. Routers only map HTTP ↔ schemas; services receive
  an explicit `Ctx` (session, settings, actor, wired adapters) — no global singletons.
- Errors are RFC 7807 `application/problem+json` with a stable `code` field. Auth is a static Bearer API
  key compared in constant time; the app refuses to start without `FLEET_API_KEY`.
- Writes are audited by a service-layer decorator (`services.audit.audited`): actor, action, target,
  outcome and a redacted summary. Failures are audited too (`outcome=error`).
- Sync (threadpool) endpoints: the work is subprocess + file IO bound and SQLite is sync anyway.

## Consequences
Swapping SQLite for MySQL is a DB URL + driver change; all schema changes go through Alembic.
