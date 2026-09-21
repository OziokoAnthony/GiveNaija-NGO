from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel, Index


class PledgeStatus(str, Enum):
    PENDING = "pending"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class Pledge(SQLModel, table=True):
    """
    Pledge created by a donor towards a specific campaign.
    """
    __tablename__ = "pledges"

    id: Optional[int] = Field(default=None, primary_key=True)
    member_id: int = Field(foreign_key="members.id", nullable=False)
    campaign_id: int = Field(foreign_key="campaigns.id", nullable=False)
    amount: int = Field(gt=0, nullable=False)  # in kobo
    status: str = Field(default=PledgeStatus.PENDING.value, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Donation(SQLModel, table=True):
    """
    Donation entity.
    Critical Hard Problem Constraint: bank_ref is globally UNIQUE.
    No bank transfer can ever be recorded twice, even under concurrent requests.
    """
    __tablename__ = "donations"
    __table_args__ = (
        Index("ix_donations_campaign_at", "campaign_id", "at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaigns.id", index=True, nullable=False)
    member_id: Optional[int] = Field(default=None, foreign_key="members.id", nullable=True)
    amount: int = Field(gt=0, nullable=False)  # in kobo
    bank_ref: str = Field(unique=True, index=True, nullable=False)  # UNIQUE constraint against double counting
    recorded_by: int = Field(foreign_key="users.id", nullable=False)
    at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )


class Receipt(SQLModel, table=True):
    """
    Numbered receipt for a recorded donation.
    Guarantees that a donation has exactly one receipt number (one-time resource).
    """
    __tablename__ = "receipts"

    id: Optional[int] = Field(default=None, primary_key=True)
    donation_id: int = Field(foreign_key="donations.id", unique=True, nullable=False)
    number: str = Field(unique=True, index=True, nullable=False)
    issued_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class IdempotencyRecord(SQLModel, table=True):
    """
    Storage for Idempotency-Key headers to guarantee exact-once execution.
    A retry with the same key returns the previously saved 200/201 response.
    """
    __tablename__ = "idempotency_keys"

    key: str = Field(primary_key=True, index=True)
    endpoint: str = Field(nullable=False)
    body_hash: str = Field(nullable=False)
    response_json: str = Field(nullable=False)
    status_code: int = Field(default=201, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
