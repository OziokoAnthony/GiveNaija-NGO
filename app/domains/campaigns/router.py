from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlmodel import Session

from app.core.deps import get_db, require_admin
from app.domains.auth.models import User
from app.domains.campaigns.schemas import CampaignCreate, CampaignListResponse, CampaignResponse
from app.domains.campaigns.service import CampaignService

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.get(
    "",
    response_model=CampaignListResponse,
    status_code=status.HTTP_200_OK,
    summary="List fundraising campaigns (Cached)",
    description="Returns a paginated list of campaigns. Responses are cached in Redis with invalidation on write.",
)
def list_campaigns(
    status: Optional[str] = Query(None, description="Filter by status: 'open' or 'closed'"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: Session = Depends(get_db),
) -> CampaignListResponse:
    """Thin route handler delegating to CampaignService."""
    return CampaignService.list_campaigns(
        session=session,
        status_filter=status,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new fundraising campaign",
    description="Admin-only endpoint to create a new campaign with target fundraising goal.",
)
def create_campaign(
    payload: CampaignCreate,
    current_user: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> CampaignResponse:
    """Thin route handler: ensures admin authorization and creates campaign."""
    campaign = CampaignService.create_campaign(
        session=session,
        data=payload,
        actor=current_user,
    )
    return CampaignResponse.model_validate(campaign)


@router.post(
    "/{id}/close",
    response_model=CampaignResponse,
    status_code=status.HTTP_200_OK,
    summary="Close an existing fundraising campaign",
    description="Admin-only endpoint to close a campaign so no further donations can be recorded against it.",
)
def close_campaign(
    id: int,
    current_user: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> CampaignResponse:
    """Thin route handler: closes campaign and audits action."""
    campaign = CampaignService.close_campaign(
        session=session,
        campaign_id=id,
        actor=current_user,
    )
    return CampaignResponse.model_validate(campaign)


@router.get(
    "/{id}/stream",
    status_code=status.HTTP_200_OK,
    summary="Live Server-Sent Events (SSE) donation stream",
    description="Keeps connection open and streams live donations to the campaign page with 15-second heartbeats.",
)
async def campaign_event_stream(
    id: int,
    request: Request,
    session: Session = Depends(get_db),
):
    """
    Streams live donation ticker updates via SSE.
    Never queries the database in a loop; uses an in-process pub/sub event bus.
    """
    import asyncio
    import json
    from starlette.responses import StreamingResponse
    from app.core.broadcaster import register_campaign_subscriber, unregister_campaign_subscriber
    from app.core.errors import AppException

    # Verify campaign exists
    campaign = session.get(Campaign, id)
    if not campaign:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="CAMPAIGN_NOT_FOUND",
            message=f"Campaign with ID {id} does not exist.",
        )

    async def event_generator():
        queue = await register_campaign_subscriber(id)
        try:
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # 15-second heartbeat comment to keep proxies/reverse proxies alive
                    yield ": heartbeat\n\n"
        finally:
            await unregister_campaign_subscriber(id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

