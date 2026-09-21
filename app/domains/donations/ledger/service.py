"""
app/domains/donations/ledger/service.py — Ledger business logic.

Rules:
    1. create_ledger_entry() is always called INSIDE the same transaction
       as record_donation() — both commit or both roll back atomically.
    2. Ledger entries are NEVER updated or deleted.
    3. get_campaign_ledger() and get_donor_ledger() are read-only queries.
"""

from __future__ import annotations

from decimal import Decimal

from sqlmodel import Session, select

from app.domains.donations.ledger.models import EntryType, LedgerEntry


def create_ledger_entry(
    session: Session,
    *,
    donation_id: int,
    campaign_id: int,
    amount_ngn: Decimal,
    entry_type: EntryType = EntryType.CREDIT,
    description: str = "",
) -> LedgerEntry:
    """
    Write one immutable ledger entry inside the caller's transaction.

    Called by DonationService.record_donation() BEFORE session.commit()
    so both the Donation row and LedgerEntry row are committed atomically.

    Args:
        session:     Active SQLModel session owned by the caller.
        donation_id: FK to donations.id (None for DEBIT/non-donation entries).
        campaign_id: FK to campaigns.id (denormalized for fast reporting).
        amount_ngn:  Exact Naira amount as Decimal — never a float.
        entry_type:  CREDIT (default), DEBIT, or REFUND.
        description: Plain-English note for reconciliation.

    Returns:
        The newly created (but not yet committed) LedgerEntry instance.
    """
    entry = LedgerEntry(
        donation_id=donation_id,
        campaign_id=campaign_id,
        entry_type=entry_type,
        amount_ngn=amount_ngn,
        description=description or f"Webhook payment NGN {amount_ngn:.2f}",
    )
    session.add(entry)
    # session.flush() makes the row visible within this transaction
    # without committing — caller will commit when ready
    session.flush()
    return entry


def get_campaign_ledger(
    session: Session,
    campaign_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[LedgerEntry]:
    """
    Return all ledger entries for a campaign ordered by date (newest first).

    Used by the finance statement endpoint.
    Access-controlled: finance or admin role required (enforced in router).

    Args:
        session:     Read-only SQLModel session.
        campaign_id: The campaign to query.
        limit:       Max rows to return (default 100, max enforced in router).
        offset:      Pagination offset.

    Returns:
        List of LedgerEntry rows, newest first.
    """
    return list(
        session.exec(
            select(LedgerEntry)
            .where(LedgerEntry.campaign_id == campaign_id)
            .order_by(LedgerEntry.recorded_at.desc())  # type: ignore[union-attr]
            .limit(limit)
            .offset(offset)
        ).all()
    )


def get_donor_ledger(
    session: Session,
    donor_user_id: int,
    limit: int = 50,
    offset: int = 0,
) -> list[LedgerEntry]:
    """
    Return ledger entries linked to donations made by a specific donor.

    Joins ledger_entries → donations on donation_id to filter by donor.
    Used by the donor's personal statement endpoint.

    Args:
        session:       Read-only SQLModel session.
        donor_user_id: The authenticated donor's user.id.
        limit:         Max rows to return.
        offset:        Pagination offset.

    Returns:
        List of LedgerEntry rows for donations made by this donor, newest first.
    """
    from app.domains.donations.models import Donation  # local import — avoids circular deps
    from app.domains.auth.models import Member

    return list(
        session.exec(
            select(LedgerEntry)
            .join(Donation, Donation.id == LedgerEntry.donation_id)
            .outerjoin(Member, Member.id == Donation.member_id)
            .where(
                (Donation.recorded_by == donor_user_id) | (Member.user_id == donor_user_id)
            )
            .order_by(LedgerEntry.recorded_at.desc())  # type: ignore[union-attr]
            .limit(limit)
            .offset(offset)
        ).all()
    )


def get_total_credited(session: Session, campaign_id: int) -> Decimal:
    """
    Sum all CREDIT entries for a campaign.

    Used to verify that ledger total matches campaigns.raised_amount.
    If these two numbers ever differ, it signals data corruption.

    Args:
        session:     Read-only SQLModel session.
        campaign_id: The campaign to sum.

    Returns:
        Total Naira credited as a Decimal (0.00 if no entries).
    """
    from sqlalchemy import func

    result = session.exec(
        select(func.sum(LedgerEntry.amount_ngn)).where(
            LedgerEntry.campaign_id == campaign_id,
            LedgerEntry.entry_type == EntryType.CREDIT,
        )
    ).first()

    return result or Decimal("0.00")
