"""
app/domains/donations/ledger/models.py — Financial ledger table.

WHAT IS A LEDGER?
    In accounting, a ledger is the permanent record of every money movement.
    Each row in this table records ONE financial event — a debit (money out)
    or a credit (money in) — and can never be updated or deleted.

    This is NOT the audit log (which records WHO did WHAT).
    This is the FINANCIAL record of HOW MUCH moved and WHERE.

WHY THIS MATTERS FOR THE HARD PROBLEM:
    "Record every Naira exactly once, with an audit trail nobody can edit."

    The LedgerEntry table enforces this at the data layer:
      - Each donation creates exactly ONE ledger CREDIT row
      - The `donation_id` FK with UNIQUE constraint prevents duplicates
      - No UPDATE / DELETE triggers (same pattern as AuditLog)
      - Finance officers can reconcile the ledger against bank records

LEDGER ENTRY TYPES:
    CREDIT — Money received into the campaign (donation recorded)
    DEBIT  — Money paid out from the campaign (future: disbursement)
    REFUND — Money returned to donor (future: refund workflow)
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlmodel import Field, Index, SQLModel


class EntryType(str, Enum):
    """
    The direction of money movement for a ledger entry.
    CREDIT = money coming IN to the NGO.
    DEBIT  = money going OUT from the NGO.
    REFUND = money returned to the donor.
    """
    CREDIT = "credit"
    DEBIT = "debit"
    REFUND = "refund"


class LedgerEntry(SQLModel, table=True):
    """
    Immutable financial ledger row.

    One row is created per donation (type=CREDIT).
    Future disbursement and refund workflows will add DEBIT/REFUND rows.

    Columns:
        id          — Auto-increment primary key.
        donation_id — FK to donations.id. UNIQUE: one ledger row per donation.
        campaign_id — Denormalized FK to campaigns.id for fast campaign totals.
        entry_type  — CREDIT / DEBIT / REFUND.
        amount_ngn  — Exact Naira amount (DECIMAL(15,2) — never a float).
        description — Human-readable note (e.g. "Webhook payment NGN 5000.00").
        recorded_at — UTC timestamp, set at insert time, never updated.
    """

    __tablename__ = "ledger_entries"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign keys (stored as plain ints — avoids circular SQLModel relationship issues)
    donation_id: Optional[int] = Field(
        default=None,
        foreign_key="donations.id",
        nullable=True,
        # UNIQUE: one ledger CREDIT per donation — enforces "record once" rule
        unique=True,
        index=True,
    )
    campaign_id: int = Field(foreign_key="campaigns.id", index=True)

    # Type of financial movement
    entry_type: EntryType = Field(default=EntryType.CREDIT)

    # Exact monetary amount in Nigerian Naira — Decimal prevents float rounding
    amount_ngn: Decimal = Field(
        max_digits=15,
        decimal_places=2,
    )

    # Human-readable description for reconciliation
    description: str = Field(default="")

    # Immutable timestamp — set once at INSERT, never updated
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        # Composite index: fast query for "all ledger entries for a campaign
        # between date A and date B" (used by the finance statement report)
        Index("ix_ledger_campaign_date", "campaign_id", "recorded_at"),
    )
