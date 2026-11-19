"""Shared fixtures. Marker is assigned from the directory a test lives in."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from hermes_fleet.app import create_app
from hermes_fleet.core.config import Settings
from hermes_fleet.db.migrate import upgrade

API_KEY = "test-api-key-not-a-secret"  # pragma: allowlist secret
AUTH = {"Authorization": f"Bearer {API_KEY}"}

_DIR_MARKERS = {
    "unit": "unit",
    "hermes": "hermes",
    "contract": "hermes",
    "ovfake": "ovfake",
    "ovreal": "ovreal",
    "e2e": "e2e",
}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        parts = Path(str(item.fspath)).parts
        for d, marker in _DIR_MARKERS.items():
            if d in parts:
                item.add_marker(getattr(pytest.mark, marker))
                break


@pytest.fixture
def fernet_key() -> str:
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode()


@pytest.fixture
def settings(tmp_path: Path, fernet_key: str) -> Settings:
    data = tmp_path / "data"
    home = tmp_path / "hermes-home"
    home.mkdir()
    return Settings(
        api_key=API_KEY,
        db_url=f"sqlite:///{tmp_path / 'fleet.db'}",
        data_dir=data,
        hermes_home=home,
        secret_key=fernet_key,
        log_json=False,
    )


@pytest.fixture
def make_client(settings: Settings) -> Iterator[Any]:
    clients: list[TestClient] = []

    def _make(deps: dict[str, Any] | None = None, s: Settings | None = None) -> TestClient:
        st = s or settings
        upgrade(st.db_url)
        c = TestClient(create_app(st, deps=deps))
        clients.append(c)
        return c

    yield _make
    for c in clients:
        c.close()


@pytest.fixture
def client(make_client: Any) -> TestClient:
    return make_client()  # type: ignore[no-any-return]


# ---------------------------------------------------------------- Hermes fixtures
REPO = Path(__file__).resolve().parent.parent
HERMES_LAUNCHER = REPO / "scripts" / "hermes"


def hermes_available() -> bool:
    import os
    import subprocess

    if os.environ.get("FLEET_SKIP_HERMES"):
        return False
    try:
        r = subprocess.run(
            [str(HERMES_LAUNCHER), "--version"], capture_output=True, text=True, timeout=120
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0 and "v0.23.1" in r.stdout


_HERMES_OK: bool | None = None


@pytest.fixture(scope="session")
def hermes_bin() -> str:
    global _HERMES_OK
    if _HERMES_OK is None:
        _HERMES_OK = hermes_available()
    if not _HERMES_OK:
        pytest.skip("hermes-agent v0.23.1 not installed (run scripts/install-hermes.sh)")
    return str(HERMES_LAUNCHER)


@pytest.fixture
def hermes_home(tmp_path: Path) -> Path:
    """An isolated, empty HERMES_HOME (Hermes borrows the venv from its owning install)."""
    home = tmp_path / "hermes-home"
    home.mkdir(exist_ok=True)
    return home


@pytest.fixture
def hermes_settings(settings: Settings, hermes_bin: str, hermes_home: Path) -> Settings:
    return settings.model_copy(update={"hermes_bin": hermes_bin, "hermes_home": hermes_home})
