from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """Safe read model for immutable audit log records."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: Optional[int]
    action: str
    target_type: str
    target_id: Optional[int]
    details: Optional[str]
    at: datetime


class AuditLogListResponse(BaseModel):
    """Paginated list of audit log entries for administrators."""
    items: List[AuditLogResponse]
    total: int
    limit: int
    offset: int
