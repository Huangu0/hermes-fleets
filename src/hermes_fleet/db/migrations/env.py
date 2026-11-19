from __future__ import annotations

import os

from alembic import context

from hermes_fleet.db import models  # noqa: F401  (register tables)
from hermes_fleet.db.base import Base, make_engine

config = context.config
if os.environ.get("FLEET_DB_URL") and not config.attributes.get("explicit_url"):
    config.set_main_option("sqlalchemy.url", os.environ["FLEET_DB_URL"])
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = make_engine(str(config.get_main_option("sqlalchemy.url")))
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
