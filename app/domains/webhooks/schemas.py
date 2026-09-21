from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PaymentWebhookPayload(BaseModel):
    """
    Schema matching incoming payload from payment provider webhook.
    """
    event_id: str = Field(..., examples=["evt_3fa85f64d9f"])
    type: str = Field(..., examples=["payment.succeeded"])
    reference: str = Field(..., examples=["BOOK-123"])
    amount: int = Field(..., gt=0, examples=[45000])  # in kobo
    currency: str = Field(default="NGN", examples=["NGN"])
    paid_at: str = Field(..., examples=["2026-09-21T11:00:00Z"])


class WebhookAckResponse(BaseModel):
    """Fast standard acknowledgment returned to payment provider."""
    received: bool = True
    event_id: str
    status: str
