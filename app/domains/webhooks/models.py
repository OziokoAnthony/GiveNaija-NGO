from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class ProcessedEvent(SQLModel, table=True):
    """
    Webhook idempotency ledger table.
    Tracks received provider event_ids to guarantee that retried webhooks
    are safely acknowledged without duplicate processing or balance updates.
    """
    __tablename__ = "processed_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: str = Field(unique=True, index=True, nullable=False)
    reference: str = Field(index=True, nullable=False)
    is_orphan: bool = Field(default=False, nullable=False)
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
