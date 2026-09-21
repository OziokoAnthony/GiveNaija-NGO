"""
app/domains/donations/ledger/router.py — Ledger HTTP endpoints.

Endpoints:
    GET /ledger/campaign/{campaign_id}   — Finance/Admin: full campaign ledger
    GET /ledger/me                       — Donor: personal payment history
    GET /ledger/campaign/{id}/verify     — Admin: reconcile ledger vs raised_amount
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.core.deps import get_current_user, require_finance, require_admin, require_donor
from app.db.session import get_db
from app.domains.auth.models import User
from app.domains.donations.ledger.models import LedgerEntry
from app.domains.donations.ledger.service import (
    get_campaign_ledger,
    get_donor_ledger,
    get_total_credited,
)

router = APIRouter(prefix="/ledger", tags=["Ledger"])


# ---------------------------------------------------------------------------
# Schema helpers (inline — small enough to avoid a separate schemas.py)
# ---------------------------------------------------------------------------

def _entry_to_dict(e: LedgerEntry) -> dict:
    return {
        "id": e.id,
        "donation_id": e.donation_id,
        "campaign_id": e.campaign_id,
        "entry_type": e.entry_type,
        "amount_ngn": str(e.amount_ngn),
        "description": e.description,
        "recorded_at": e.recorded_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# GET /ledger/campaign/{campaign_id}
# ---------------------------------------------------------------------------

@router.get(
    "/campaign/{campaign_id}",
    summary="Campaign ledger (Finance / Admin)",
    status_code=status.HTTP_200_OK,
)
def get_campaign_ledger_endpoint(
    campaign_id: int,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
    _current_user: User = Depends(require_finance),
) -> dict:
    """
    Return every ledger entry for a campaign (newest first).

    Who can call: finance officer or admin.
    Use this to reconcile what the system recorded vs bank statements.

    Args:
        campaign_id: The campaign to query.
        limit:       Maximum rows to return (max 500).
        offset:      Pagination offset.
    """
    entries = get_campaign_ledger(session, campaign_id, limit=limit, offset=offset)
    return {
        "campaign_id": campaign_id,
        "count": len(entries),
        "entries": [_entry_to_dict(e) for e in entries],
    }


# ---------------------------------------------------------------------------
# GET /ledger/me
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    summary="My payment ledger (Donor)",
    status_code=status.HTTP_200_OK,
)
def get_my_ledger(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
    current_user: User = Depends(require_donor),
) -> dict:
    """
    Return the authenticated donor's personal payment history from the ledger.

    Who can call: any donor (their own data only).
    """
    entries = get_donor_ledger(session, current_user.id, limit=limit, offset=offset)
    return {
        "donor_id": current_user.id,
        "count": len(entries),
        "entries": [_entry_to_dict(e) for e in entries],
    }


# ---------------------------------------------------------------------------
# GET /ledger/campaign/{campaign_id}/verify
# ---------------------------------------------------------------------------

@router.get(
    "/campaign/{campaign_id}/verify",
    summary="Verify ledger vs campaign raised_amount (Admin)",
    status_code=status.HTTP_200_OK,
)
def verify_campaign_ledger(
    campaign_id: int,
    session: Session = Depends(get_db),
    _current_user: User = Depends(require_admin),
) -> dict:
    """
    Cross-check: sum all CREDIT ledger entries and compare to
    campaigns.raised_amount. If they differ, something is wrong.

    Who can call: admin only.

    Returns:
        ledger_total:   Sum of ledger CREDIT rows (authoritative).
        campaign_total: campaigns.raised_amount (denormalized counter).
        match:          True if both match — False signals data corruption.
    """
    from app.domains.campaigns.models import Campaign

    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found.",
        )

    from decimal import Decimal

    ledger_total = get_total_credited(session, campaign_id)
    campaign_raised_kobo = Decimal(campaign.raised_amount)
    campaign_raised_ngn = campaign_raised_kobo / Decimal(100)
    match = (ledger_total == campaign_raised_ngn) or (ledger_total == campaign_raised_kobo)

    return {
        "campaign_id": campaign_id,
        "ledger_total_ngn": str(ledger_total),
        "campaign_raised_amount_ngn": str(campaign_raised_ngn),
        "match": match,
        "status": "OK" if match else "MISMATCH — investigate immediately",
    }
