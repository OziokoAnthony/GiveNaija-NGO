import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlmodel import Session, select, func
from sqlalchemy.exc import IntegrityError
from fastapi import status

from app.core.errors import AppException
from app.db.redis import invalidate_cache
from app.domains.audit.models import AuditLog
from app.domains.auth.models import User, Member, UserRole
from app.domains.campaigns.models import Campaign, CampaignStatus
from app.domains.donations.models import Donation, Pledge, PledgeStatus, Receipt, IdempotencyRecord
from app.domains.donations.schemas import (
    DonationCreate,
    DonationResponse,
    PledgeCreate,
    StatementReportResponse,
    StatementItem,
)


class DonationService:
    """
    Core domain service enforcing the Hard Problem invariants:
    1. Exactly-once donation recording via UNIQUE bank_ref constraint and Idempotency-Key.
    2. Single atomic transaction updating campaign totals and audit logs simultaneously.
    3. Receipt uniqueness: a donation gets exactly one receipt number forever.
    """

    @staticmethod
    def record_donation(
        session: Session,
        data: DonationCreate,
        actor: User,
        idempotency_key: Optional[str] = None,
        endpoint: str = "/api/v1/donations",
    ) -> Tuple[DonationResponse, int]:
        """
        Records a donation atomically.
        Returns (DonationResponse, status_code).
        Status code is 200 for replayed idempotency keys, 201 for new creations.
        """
        # --- IDEMPOTENCY GUARD ---
        if idempotency_key:
            record = session.get(IdempotencyRecord, idempotency_key)
            if record:
                # Return previously saved exact response
                saved_data = json.loads(record.response_json)
                return DonationResponse(**saved_data), status.HTTP_200_OK

        # --- CAMPAIGN VALIDATION ---
        campaign = session.get(Campaign, data.campaign_id)
        if not campaign:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="CAMPAIGN_NOT_FOUND",
                message=f"Campaign with ID {data.campaign_id} does not exist.",
            )

        if campaign.status != CampaignStatus.OPEN.value:
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                code="CAMPAIGN_CLOSED",
                message=f"Cannot record donation: Campaign '{campaign.title}' is closed.",
            )

        # --- UNIQUE BANK REF PRE-CHECK ---
        existing_bank_ref = session.exec(
            select(Donation).where(Donation.bank_ref == data.bank_ref)
        ).first()
        if existing_bank_ref:
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                code="DUPLICATE_BANK_REFERENCE",
                message=f"Bank reference '{data.bank_ref}' has already been recorded.",
            )

        try:
            # 1. Insert Donation
            donation = Donation(
                campaign_id=data.campaign_id,
                member_id=data.member_id,
                amount=data.amount,
                bank_ref=data.bank_ref,
                recorded_by=actor.id,
                at=datetime.now(timezone.utc),
            )
            session.add(donation)
            session.flush()

            # 2. Update Campaign Raised Amount
            campaign.raised_amount += data.amount
            campaign.updated_at = datetime.now(timezone.utc)
            session.add(campaign)

            # 3. Create Immutable Financial Ledger Row
            from decimal import Decimal
            from app.domains.donations.ledger.models import EntryType
            from app.domains.donations.ledger.service import create_ledger_entry

            create_ledger_entry(
                session,
                donation_id=donation.id,
                campaign_id=campaign.id,
                amount_ngn=Decimal(donation.amount) / Decimal(100),
                entry_type=EntryType.CREDIT,
                description=f"Recorded donation {donation.bank_ref}",
            )

            # 4. Add Immutable Audit Log Row
            audit = AuditLog(
                actor_id=actor.id,
                action="RECORD_DONATION",
                target_type="donations",
                target_id=donation.id,
                details=f"Recorded donation of {donation.amount} kobo with ref {donation.bank_ref}",
            )
            session.add(audit)

            # 4. Save Idempotency Record if key provided
            response_obj = DonationResponse.model_validate(donation)
            if idempotency_key:
                body_hash = hashlib.sha256(
                    json.dumps(data.model_dump(), sort_keys=True).encode()
                ).hexdigest()
                idem_rec = IdempotencyRecord(
                    key=idempotency_key,
                    endpoint=endpoint,
                    body_hash=body_hash,
                    response_json=response_obj.model_dump_json(),
                    status_code=status.HTTP_201_CREATED,
                )
                session.add(idem_rec)

            # Atomic commit
            session.commit()
            session.refresh(donation)

            # Invalidate Redis cached campaign lists
            invalidate_cache("cache:campaigns:*")

            return response_obj, status.HTTP_201_CREATED

        except IntegrityError:
            session.rollback()
            # Catches concurrent race conditions on bank_ref unique constraint
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                code="DUPLICATE_BANK_REFERENCE",
                message=f"Bank reference '{data.bank_ref}' was recorded concurrently.",
            )
        except Exception:
            session.rollback()
            raise

    @staticmethod
    def get_or_create_receipt(
        session: Session,
        donation_id: int,
        current_user: User,
    ) -> Receipt:
        """
        Retrieves or generates a numbered receipt for a donation.
        Guarantees that requesting a receipt twice returns the exact same number.
        """
        donation = session.get(Donation, donation_id)
        if not donation:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="DONATION_NOT_FOUND",
                message=f"Donation with ID {donation_id} was not found.",
            )

        # Authorization: Donor can only view their own receipts; finance/admin can view any
        if current_user.role == UserRole.DONOR.value:
            member = session.exec(
                select(Member).where(Member.user_id == current_user.id)
            ).first()
            if not member or donation.member_id != member.id:
                raise AppException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    code="FORBIDDEN_RECEIPT_ACCESS",
                    message="You do not have permission to access receipts for this donation.",
                )

        # Check if receipt already exists
        existing_receipt = session.exec(
            select(Receipt).where(Receipt.donation_id == donation_id)
        ).first()
        if existing_receipt:
            return existing_receipt

        # Generate receipt once
        try:
            receipt_num = f"RCPT-{donation.id:06d}-{donation.at.strftime('%Y%m%d%H%M')}"
            receipt = Receipt(
                donation_id=donation.id,
                number=receipt_num,
                issued_at=datetime.now(timezone.utc),
            )
            session.add(receipt)
            session.commit()
            session.refresh(receipt)
            return receipt
        except IntegrityError:
            session.rollback()
            # If generated concurrently, fetch the winner
            receipt = session.exec(
                select(Receipt).where(Receipt.donation_id == donation_id)
            ).first()
            if receipt:
                return receipt
            raise

    @staticmethod
    def create_pledge(
        session: Session,
        data: PledgeCreate,
        current_user: User,
    ) -> Pledge:
        member = session.exec(
            select(Member).where(Member.user_id == current_user.id)
        ).first()
        if not member:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="MEMBER_NOT_FOUND",
                message="Member profile not found for the current donor account.",
            )

        campaign = session.get(Campaign, data.campaign_id)
        if not campaign:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="CAMPAIGN_NOT_FOUND",
                message=f"Campaign with ID {data.campaign_id} does not exist.",
            )

        if campaign.status != CampaignStatus.OPEN.value:
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                code="CAMPAIGN_CLOSED",
                message=f"Campaign '{campaign.title}' is closed to new pledges.",
            )

        try:
            pledge = Pledge(
                member_id=member.id,
                campaign_id=data.campaign_id,
                amount=data.amount,
                status=PledgeStatus.PENDING.value,
            )
            session.add(pledge)
            session.flush()

            audit = AuditLog(
                actor_id=current_user.id,
                action="CREATE_PLEDGE",
                target_type="pledges",
                target_id=pledge.id,
                details=f"Pledged {pledge.amount} kobo to campaign {campaign.id}",
            )
            session.add(audit)

            session.commit()
            session.refresh(pledge)
            return pledge
        except Exception:
            session.rollback()
            raise

    @staticmethod
    def get_statement(
        session: Session,
        from_date: datetime,
        to_date: datetime,
    ) -> StatementReportResponse:
        donations = session.exec(
            select(Donation)
            .where(Donation.at >= from_date, Donation.at <= to_date)
            .order_by(Donation.at.asc())
        ).all()

        total_amount = sum(d.amount for d in donations)
        items = [StatementItem.model_validate(d) for d in donations]

        return StatementReportResponse(
            period_from=from_date,
            period_to=to_date,
            total_donations=len(donations),
            total_amount=total_amount,
            items=items,
        )
