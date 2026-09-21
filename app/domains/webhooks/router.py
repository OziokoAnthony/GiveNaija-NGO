from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlmodel import Session

from app.core.broadcaster import broadcast_donation_event
from app.core.config import settings
from app.core.security import verify_webhook_signature
from app.db.firestore import sync_donation_to_feed
from app.db.session import get_db
from app.domains.webhooks.schemas import PaymentWebhookPayload, WebhookAckResponse
from app.domains.webhooks.service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["Payment Webhook"])


async def trigger_webhook_background_tasks(donation_data: dict) -> None:
    """Async background processing: Firestore feed sync and SSE push."""
    campaign_id = donation_data.get("campaign_id")
    sync_donation_to_feed(campaign_id, donation_data)
    await broadcast_donation_event(campaign_id, donation_data)


@router.post(
    "/payment",
    response_model=WebhookAckResponse,
    status_code=status.HTTP_200_OK,
    summary="Receive payment provider signed webhook",
    description="Webhook endpoint called by payment provider upon donor payment. Verified with HMAC-SHA256.",
)
async def payment_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_signature: str = Header(..., alias="X-Signature"),
    session: Session = Depends(get_db),
) -> WebhookAckResponse:
    # 1. Read raw request body bytes for exact HMAC-SHA256 verification
    raw_body = await request.body()

    # 2. Verify signature with constant-time comparison
    if not verify_webhook_signature(raw_body, x_signature, settings.WEBHOOK_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Signature header.",
        )

    # 3. Parse JSON payload
    try:
        payload = PaymentWebhookPayload.model_validate_json(raw_body)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Malformed webhook JSON payload: {e}",
        )

    # 4. Process webhook with idempotency & orphan checks
    ack, donation_data = WebhookService.process_payment(
        session=session,
        payload=payload,
    )

    # 5. Hand off non-blocking work to background task
    if donation_data:
        background_tasks.add_task(trigger_webhook_background_tasks, donation_data)

    return ack
