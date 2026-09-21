from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.deps import get_db, require_admin
from app.domains.auth.models import User
from app.domains.audit.schemas import AuditLogListResponse
from app.domains.audit.service import AuditService

router = APIRouter(prefix="/admin", tags=["Audit Log & Administration"])


@router.get(
    "/audit-log",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect immutable audit log (Admin only)",
    description="Lists chronological audit entries detailing who did what, to which record, and when.",
)
def get_audit_log(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    actor: Optional[int] = Query(None, description="Filter actions by user ID"),
    current_user: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> AuditLogListResponse:
    """Thin route handler delegating to AuditService."""
    return AuditService.list_logs(
        session=session,
        actor_id=actor,
        limit=limit,
        offset=offset,
    )
