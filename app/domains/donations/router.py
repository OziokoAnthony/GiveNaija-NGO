from datetime import datetime
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, Response, status
from sqlmodel import Session, select, func

from app.core.broadcaster import broadcast_donation_event
from app.core.deps import get_db, get_current_user, require_finance, require_donor
from app.db.firestore import sync_donation_to_feed
from app.domains.auth.models import User, Member
from app.domains.donations.models import Donation, Receipt
from app.domains.donations.schemas import (
    DonationCreate,
    DonationResponse,
    DonationListResponse,
    PledgeCreate,
    PledgeResponse,
    ReceiptResponse,
    StatementReportResponse,
)
from app.domains.donations.service import DonationService

router = APIRouter(tags=["Donations & Pledges"])


async def trigger_post_donation_tasks(donation_dict: dict) -> None:
    """
    Background tasks executed after HTTP 201 response:
    1. Push to Firestore live feed: donation_feed/{campaign_id}
    2. Broadcast to Server-Sent Events (SSE) live campaign stream
    3. Simulated thank-you email/receipt generation
    """
    campaign_id = donation_dict.get("campaign_id")
    # 1. Firestore
    sync_donation_to_feed(campaign_id=campaign_id, donation_data=donation_dict)
    # 2. SSE Broadcaster
    await broadcast_donation_event(campaign_id=campaign_id, event_payload=donation_dict)


@router.post(
    "/donations",
    response_model=DonationResponse,
    summary="Record a confirmed bank transfer as a donation (Idempotent)",
    description="Finance officer records a confirmed donation. Requires UNIQUE bank_ref and supports Idempotency-Key.",
)
async def record_donation(
    payload: DonationCreate,
    response: Response,
    background_tasks: BackgroundTasks,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(require_finance),
    session: Session = Depends(get_db),
) -> DonationResponse:
    """
    Thin route handler for recording donations.
    Sets status 201 for new donations, 200 for idempotent re-sends.
    """
    donation_resp, status_code = DonationService.record_donation(
        session=session,
        data=payload,
        actor=current_user,
        idempotency_key=idempotency_key,
        endpoint="/api/v1/donations",
    )
    response.status_code = status_code

    if status_code == status.HTTP_201_CREATED:
        # Launch non-blocking background tasks
        background_tasks.add_task(trigger_post_donation_tasks, donation_resp.model_dump())

    return donation_resp


@router.post(
    "/pledges",
    response_model=PledgeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Pledge an amount to a campaign",
    description="Allows an authenticated donor to pledge funds towards an open campaign.",
)
def create_pledge(
    payload: PledgeCreate,
    current_user: User = Depends(require_donor),
    session: Session = Depends(get_db),
) -> PledgeResponse:
    pledge = DonationService.create_pledge(
        session=session,
        data=payload,
        current_user=current_user,
    )
    return PledgeResponse.model_validate(pledge)


@router.get(
    "/donations/me",
    response_model=DonationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List donations for current donor",
    description="Donors view their own personal donation history and receipts.",
)
def get_my_donations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_donor),
    session: Session = Depends(get_db),
) -> DonationListResponse:
    member = session.exec(select(Member).where(Member.user_id == current_user.id)).first()
    if not member:
        return DonationListResponse(items=[], total=0, limit=limit, offset=offset)

    query = select(Donation).where(Donation.member_id == member.id)
    total = session.exec(select(func.count()).select_from(query.subquery())).one()
    donations = session.exec(
        query.offset(offset).limit(limit).order_by(Donation.at.desc())
    ).all()

    items = [DonationResponse.model_validate(d) for d in donations]
    return DonationListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/receipts/{donation_id}",
    response_model=ReceiptResponse,
    status_code=status.HTTP_200_OK,
    summary="Get numbered receipt for a donation",
    description="Returns the single permanent receipt for a donation. Always returns the same receipt number.",
)
def get_receipt(
    donation_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ReceiptResponse:
    receipt = DonationService.get_or_create_receipt(
        session=session,
        donation_id=donation_id,
        current_user=current_user,
    )
    donation = session.get(Donation, donation_id)
    return ReceiptResponse(
        id=receipt.id,
        donation_id=donation.id,
        number=receipt.number,
        amount=donation.amount,
        bank_ref=donation.bank_ref,
        campaign_id=donation.campaign_id,
        issued_at=receipt.issued_at,
    )


@router.get(
    "/reports/statement",
    response_model=StatementReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Export donation statement for auditing",
    description="Finance officers export all donations within a date range for bank reconciliation.",
)
def get_statement(
    from_date: datetime = Query(..., alias="from"),
    to_date: datetime = Query(..., alias="to"),
    current_user: User = Depends(require_finance),
    session: Session = Depends(get_db),
) -> StatementReportResponse:
    return DonationService.get_statement(
        session=session,
        from_date=from_date,
        to_date=to_date,
    )
