"""
alembic/env.py — Alembic migration environment.

Reads DATABASE_URL from app.core.config.settings at runtime so migrations
always target the right database without any hardcoded credentials.
All SQLModel table models are imported here so Alembic can detect changes.
"""
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlmodel import SQLModel

# Ensure the project root is on PYTHONPATH so imports resolve correctly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings

# Import app.db.base — this one import triggers ALL domain model imports
# (see app/db/base.py for the full list and explanation)
import app.db.base  # noqa: F401

# Alembic Config object from alembic.ini
config = context.config

# Configure Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use SQLModel metadata as the target (Alembic inspects this for schema changes)
target_metadata = SQLModel.metadata


def get_url() -> str:
    """Return the live DATABASE_URL from settings (respects .env file)."""
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Emits SQL to stdout — used for review or dry-run before applying.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    Creates a real database connection and applies migrations within a transaction.
    """
    from sqlalchemy import create_engine

    connectable = create_engine(get_url())

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
