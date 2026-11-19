"""Programmatic Alembic upgrade/downgrade."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

_HERE = Path(__file__).parent


def alembic_config(db_url: str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(_HERE / "migrations"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    cfg.attributes["explicit_url"] = True
    return cfg


def upgrade(db_url: str, rev: str = "head") -> None:
    command.upgrade(alembic_config(db_url), rev)


def downgrade(db_url: str, rev: str = "base") -> None:
    command.downgrade(alembic_config(db_url), rev)
