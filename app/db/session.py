import logging
from typing import Generator
from sqlalchemy import text
from sqlmodel import Session, create_engine, SQLModel
from app.core.config import settings

logger = logging.getLogger(__name__)

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)

# Test connection; fallback to local SQLite if localhost PostgreSQL is unavailable or credentials differ
try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except Exception as e:
    logger.warning(
        f"PostgreSQL connection to {settings.DATABASE_URL} could not be established ({e}). "
        f"Falling back to local SQLite engine: sqlite:///./givenaija.db"
    )
    engine = create_engine(
        "sqlite:///./givenaija.db",
        echo=False,
        connect_args={"check_same_thread": False},
    )


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session per request.
    Closes the session when the request finishes.
    """
    with Session(engine) as session:
        yield session


def init_db() -> None:
    """Create all tables registered in SQLModel metadata."""
    SQLModel.metadata.create_all(engine)
