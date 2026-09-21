from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CampaignCreate(BaseModel):
    """Payload for creating a new fundraising campaign."""
    title: str = Field(..., min_length=3, examples=["Borehole for Ikot Ekpene"])
    description: Optional[str] = Field(None, examples=["Clean water project for 5,000 residents"])
    goal_amount: int = Field(..., gt=0, examples=[200000000])  # in kobo (e.g. 2,000,000 NGN = 200,000,000 kobo)


class CampaignResponse(BaseModel):
    """Public campaign details."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str]
    goal_amount: int
    raised_amount: int
    status: str
    created_at: datetime
    updated_at: datetime


class CampaignListResponse(BaseModel):
    """Paginated list of campaigns."""
    items: List[CampaignResponse]
    total: int
    limit: int
    offset: int
    cached: bool = False
