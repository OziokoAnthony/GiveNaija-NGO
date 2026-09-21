from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DonationCreate(BaseModel):
    """Payload to record a confirmed donation."""
    campaign_id: int = Field(..., examples=[1])
    amount: int = Field(..., gt=0, examples=[2000000])  # in kobo (e.g. 20,000 NGN)
    bank_ref: str = Field(..., min_length=4, examples=["TXN-GTB-20260921-001"])
    member_id: Optional[int] = Field(None, examples=[1])


class DonationResponse(BaseModel):
    """Details of a recorded donation."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    member_id: Optional[int]
    amount: int
    bank_ref: str
    recorded_by: int
    at: datetime


class PledgeCreate(BaseModel):
    """Payload to create a pledge towards a campaign."""
    campaign_id: int = Field(..., examples=[1])
    amount: int = Field(..., gt=0, examples=[5000000])


class PledgeResponse(BaseModel):
    """Pledge record details."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: int
    campaign_id: int
    amount: int
    status: str
    created_at: datetime


class ReceiptResponse(BaseModel):
    """Numbered tax/donation receipt."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    donation_id: int
    number: str
    amount: int
    bank_ref: str
    campaign_id: int
    issued_at: datetime


class DonationListResponse(BaseModel):
    """Paginated list of donations."""
    items: List[DonationResponse]
    total: int
    limit: int
    offset: int


class StatementItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    amount: int
    bank_ref: str
    recorded_by: int
    at: datetime


class StatementReportResponse(BaseModel):
    """Auditable financial statement for a specific time window."""
    period_from: datetime
    period_to: datetime
    total_donations: int
    total_amount: int
    items: List[StatementItem]
