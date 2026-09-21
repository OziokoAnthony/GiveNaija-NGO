from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel


class CampaignStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class Campaign(SQLModel, table=True):
    """
    Campaign model representing a fundraising target.
    Carries goal_amount and current raised_amount.
    """
    __tablename__ = "campaigns"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True, nullable=False)
    description: Optional[str] = Field(default=None, nullable=True)
    goal_amount: int = Field(gt=0, nullable=False)  # in smallest unit (kobo)
    raised_amount: int = Field(default=0, ge=0, nullable=False)
    status: str = Field(
        default=CampaignStatus.OPEN.value,
        index=True,
        nullable=False,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
