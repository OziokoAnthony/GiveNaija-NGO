"""
app/db/migrations.py — Programmatic Alembic migration runner.

WHY THIS EXISTS:
    In production (Docker / CI / cloud), you cannot always run
    `alembic upgrade head` manually before starting the server.
    This module lets main.py call run_migrations() during the lifespan
    startup hook so the database schema is always up-to-date before
    the first request is served.

USAGE IN main.py lifespan:
    from app.db.migrations import run_migrations
    run_migrations()

SAFETY:
    - Alembic tracks applied migrations in the `alembic_version` table.
      Running upgrade head when already up-to-date is a no-op — safe to
      call on every startup.
    - If the DB is unreachable, the error bubbles up and the server
      refuses to start — which is correct (better than silent failure).

SKIPPED IN TESTING:
    When APP_ENV == "testing", main.py's lifespan skips this call.
    Tests use SQLite in memory and manage schema via SQLModel.metadata.create_all().
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)

# Absolute path to alembic.ini — works regardless of where the process is started
_ALEMBIC_INI = str(Path(__file__).resolve().parents[2] / "alembic.ini")


def run_migrations() -> None:
    """
    Apply all pending Alembic migrations (upgrade to head).

    Equivalent to running:  uv run alembic upgrade head

    Called once during application startup lifespan.
    Raises an exception and prevents startup if migration fails.
    """
    logger.info("Running Alembic migrations (upgrade head)...")

    # Load Alembic config from alembic.ini
    alembic_cfg = Config(_ALEMBIC_INI)

    # Apply all pending migrations
    # If already at head, this is a safe no-op
    command.upgrade(alembic_cfg, "head")

    logger.info("Alembic migrations complete. Database schema is up to date.")


def stamp_head() -> None:
    """
    Mark the current DB state as 'head' without running any migrations.

    Use this ONCE when the DB was created directly via SQLModel.metadata.create_all()
    (e.g., by the seed script) and you want Alembic to take over from here.

    Equivalent to:  uv run alembic stamp head
    """
    alembic_cfg = Config(_ALEMBIC_INI)
    command.stamp(alembic_cfg, "head")
    logger.info("Database stamped as Alembic head.")
