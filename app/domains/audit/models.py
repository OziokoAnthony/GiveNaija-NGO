from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    """
    Append-only audit log table.
    Records who did what, to which record, and when.
    Every service function that mutates state writes an audit row
    inside the same transaction.
    """
    __tablename__ = "audit_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    actor_id: Optional[int] = Field(default=None, foreign_key="users.id", nullable=True)
    action: str = Field(index=True, nullable=False)
    target_type: str = Field(nullable=False)
    target_id: Optional[int] = Field(default=None, nullable=True)
    details: Optional[str] = Field(default=None, nullable=True)
    at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
