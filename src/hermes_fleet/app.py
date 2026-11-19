"""FastAPI application factory."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from hermes_fleet import __version__
from hermes_fleet.api.v1.router import api_router
from hermes_fleet.core.config import Settings, get_settings
from hermes_fleet.core.errors import install_handlers
from hermes_fleet.core.logging import configure_logging
from hermes_fleet.db.base import make_engine, make_session_factory
from hermes_fleet.services.wiring import build_deps


def create_app(settings: Settings | None = None, *, deps: dict[str, Any] | None = None) -> FastAPI:
    settings = settings or get_settings()
    api_key = settings.require_api_key()  # fail fast with a clear message
    configure_logging(settings.log_json)

    app = FastAPI(
        title="hermes-fleet",
        version=__version__,
        description="Desired-state control plane for hermes-agent profiles.",
    )
    engine = make_engine(settings.db_url)
    app.state.settings = settings
    app.state.api_key = api_key
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.deps = build_deps(settings, overrides=deps)

    install_handlers(app)

    @app.get("/healthz", tags=["ops"])
    def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    app.include_router(api_router)
    return app
