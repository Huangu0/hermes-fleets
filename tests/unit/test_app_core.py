from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from hermes_fleet.app import create_app
from hermes_fleet.core.config import ConfigError, Settings
from hermes_fleet.db.base import make_engine
from hermes_fleet.db.migrate import downgrade, upgrade
from tests.conftest import AUTH

PROBLEM_KEYS = {"type", "title", "status", "detail", "code", "instance"}


def test_healthz_ok_without_auth(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_missing_api_key_fails_fast(settings: Settings) -> None:
    s = settings.model_copy(update={"api_key": None})
    with pytest.raises(ConfigError, match="FLEET_API_KEY"):
        create_app(s)


def test_401_problem(client: TestClient) -> None:
    r = client.get("/v1/audit")
    assert r.status_code == 401
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json().keys() >= PROBLEM_KEYS
    r2 = client.get("/v1/audit", headers={"Authorization": "Bearer wrong"})
    assert r2.status_code == 401
    assert r2.json()["code"] == "unauthorized"


def test_404_problem(client: TestClient) -> None:
    r = client.get("/v1/nope", headers=AUTH)
    assert r.status_code == 404
    body = r.json()
    assert body.keys() >= PROBLEM_KEYS and body["code"] == "not_found"


def test_422_problem(client: TestClient) -> None:
    r = client.get("/v1/audit?limit=0", headers=AUTH)
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "validation_error" and body["errors"]


def test_openapi_lists_v1(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert "/v1/audit" in spec["paths"]


def test_alembic_roundtrip_and_pragmas(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'm.db'}"
    upgrade(url)
    eng = make_engine(url)
    tables = set(inspect(eng).get_table_names())
    assert "audit_log" in tables
    with eng.connect() as c:
        assert c.exec_driver_sql("PRAGMA journal_mode").scalar() == "wal"
        assert c.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
    eng.dispose()
    downgrade(url)
    con = sqlite3.connect(tmp_path / "m.db")
    names = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    con.close()
    assert names <= {"alembic_version"}
    upgrade(url)  # and back up again
