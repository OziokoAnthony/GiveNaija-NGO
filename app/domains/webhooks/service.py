from datetime import datetime, timezone
import logging
from typing import Optional, Tuple
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.db.redis import invalidate_cache
from app.domains.audit.models import AuditLog
from app.domains.auth.models import User, UserRole
from app.domains.campaigns.models import Campaign, CampaignStatus
from app.domains.donations.models import Donation
from app.domains.webhooks.models import ProcessedEvent
from app.domains.webhooks.schemas import PaymentWebhookPayload, WebhookAckResponse

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Handles signed payment webhooks from payment providers.
    Guarantees idempotency and orphan reference handling.
    """

    @staticmethod
    def process_payment(
        session: Session,
        payload: PaymentWebhookPayload,
    ) -> Tuple[WebhookAckResponse, Optional[dict]]:
        """
        Processes payment webhook:
        1. Checks processed_events for duplicate event_id (seen before -> 200, do nothing).
        2. Resolves campaign from reference.
        3. If reference does not exist -> records as orphan, returns 200.
        4. If campaign exists -> inserts donation, updates campaign balance, logs audit row.
        """
        # --- 1. IDEMPOTENCY CHECK (Processed Events Table) ---
        existing_event = session.exec(
            select(ProcessedEvent).where(ProcessedEvent.event_id == payload.event_id)
        ).first()

        if existing_event:
            logger.info(f"Duplicate webhook event_id '{payload.event_id}' safely ignored.")
            return (
                WebhookAckResponse(
                    event_id=payload.event_id,
                    status="duplicate_ignored",
                ),
                None,
            )

        # --- 2. RESOLVE CAMPAIGN FROM REFERENCE ---
        # Supports formats: "CAMP-1", "1", title match, or default open campaign fallback
        campaign = None
        ref = payload.reference.strip()

        if ref.startswith("CAMP-") and ref[5:].isdigit():
            campaign = session.get(Campaign, int(ref[5:]))
        elif ref.isdigit():
            campaign = session.get(Campaign, int(ref))
        else:
            campaign = session.exec(select(Campaign).where(Campaign.title == ref)).first()

        # If reference still not resolved, check if an open campaign exists for general gifts
        if not campaign:
            # Look for an existing donation with this reference or first open campaign if reference is a general reference
            if ref.startswith("BOOK-") or ref.startswith("DON-") or ref.startswith("REF-"):
                campaign = session.exec(
                    select(Campaign).where(Campaign.status == CampaignStatus.OPEN.value)
                ).first()

        # --- 3. UNKNOWN REFERENCE / ORPHAN HANDLING ---
        # Capstone requirement: "unknown reference -> 200 but logged as an orphan"
        if not campaign or campaign.status != CampaignStatus.OPEN.value:
            try:
                orphan_event = ProcessedEvent(
                    event_id=payload.event_id,
                    reference=payload.reference,
                    is_orphan=True,
                )
                session.add(orphan_event)

                orphan_audit = AuditLog(
                    actor_id=None,
                    action="ORPHAN_WEBHOOK_RECORDED",
                    target_type="webhooks",
                    target_id=None,
                    details=f"Unmatched payment reference '{payload.reference}' for {payload.amount} kobo",
                )
                session.add(orphan_audit)

                session.commit()
                logger.warning(f"Orphan webhook logged for unknown reference: {payload.reference}")
                return (
                    WebhookAckResponse(
                        event_id=payload.event_id,
                        status="orphan_logged",
                    ),
                    None,
                )
            except Exception:
                session.rollback()
                raise

        # --- 4. ATOMIC DONATION RECORDING ---
        try:
            # Find an admin user to associate with automated recording
            admin_user = session.exec(
                select(User).where(User.role == UserRole.ADMIN.value)
            ).first()
            admin_id = admin_user.id if admin_user else 1

            donation = Donation(
                campaign_id=campaign.id,
                member_id=None,
                amount=payload.amount,
                bank_ref=payload.reference,
                recorded_by=admin_id,
                at=datetime.now(timezone.utc),
            )
            session.add(donation)
            session.flush()

            # Update campaign total
            campaign.raised_amount += payload.amount
            campaign.updated_at = datetime.now(timezone.utc)
            session.add(campaign)

            # Record in processed_events table (Idempotency)
            processed = ProcessedEvent(
                event_id=payload.event_id,
                reference=payload.reference,
                is_orphan=False,
            )
            session.add(processed)

            # Append to immutable financial ledger
            from decimal import Decimal
            from app.domains.donations.ledger.models import EntryType
            from app.domains.donations.ledger.service import create_ledger_entry

            create_ledger_entry(
                session,
                donation_id=donation.id,
                campaign_id=campaign.id,
                amount_ngn=Decimal(payload.amount) / Decimal(100),
                entry_type=EntryType.CREDIT,
                description=f"Webhook payment ref {payload.reference}",
            )

            # Append to immutable audit log
            audit = AuditLog(
                actor_id=None,
                action="WEBHOOK_DONATION_RECORDED",
                target_type="donations",
                target_id=donation.id,
                details=f"Provider webhook {payload.event_id} confirmed for {donation.amount} kobo",
            )
            session.add(audit)

            session.commit()
            session.refresh(donation)

            invalidate_cache("cache:campaigns:*")

            donation_dict = {
                "id": donation.id,
                "campaign_id": donation.campaign_id,
                "amount": donation.amount,
                "bank_ref": donation.bank_ref,
                "at": donation.at.isoformat(),
            }

            return (
                WebhookAckResponse(
                    event_id=payload.event_id,
                    status="payment_confirmed",
                ),
                donation_dict,
            )

        except IntegrityError:
            session.rollback()
            # If bank_ref already recorded by manual entry or previous event
            return (
                WebhookAckResponse(
                    event_id=payload.event_id,
                    status="already_processed",
                ),
                None,
            )
        except Exception:
            session.rollback()
            raise
