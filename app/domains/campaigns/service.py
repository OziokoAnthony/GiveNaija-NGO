from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Session, select, func
from fastapi import status

from app.core.errors import AppException
from app.db.redis import get_cache, set_cache, invalidate_cache
from app.domains.audit.models import AuditLog
from app.domains.auth.models import User
from app.domains.campaigns.models import Campaign, CampaignStatus
from app.domains.campaigns.schemas import CampaignCreate, CampaignListResponse, CampaignResponse


class CampaignService:
    """
    Business logic for Campaign lifecycle, Redis caching, and audit logging.
    """

    @staticmethod
    def list_campaigns(
        session: Session,
        status_filter: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> CampaignListResponse:
        cache_key = f"cache:campaigns:{status_filter or 'all'}:{limit}:{offset}"
        cached_data = get_cache(cache_key)
        if cached_data:
            cached_data["cached"] = True
            return CampaignListResponse(**cached_data)

        # Database Query
        query = select(Campaign)
        if status_filter:
            query = query.where(Campaign.status == status_filter)

        total = session.exec(select(func.count()).select_from(query.subquery())).one()
        campaigns = session.exec(
            query.offset(offset).limit(limit).order_by(Campaign.created_at.desc())
        ).all()

        items = [CampaignResponse.model_validate(c) for c in campaigns]
        response = CampaignListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            cached=False,
        )

        # Store in Redis for 60 seconds (hot read)
        set_cache(cache_key, response.model_dump(), ttl_seconds=60)
        return response

    @staticmethod
    def create_campaign(
        session: Session,
        data: CampaignCreate,
        actor: User,
    ) -> Campaign:
        try:
            campaign = Campaign(
                title=data.title,
                description=data.description,
                goal_amount=data.goal_amount,
                status=CampaignStatus.OPEN.value,
            )
            session.add(campaign)
            session.flush()

            # Record staff action in audit log in the SAME transaction
            audit = AuditLog(
                actor_id=actor.id,
                action="CREATE_CAMPAIGN",
                target_type="campaigns",
                target_id=campaign.id,
                details=f"Created campaign '{campaign.title}' with goal {campaign.goal_amount}",
            )
            session.add(audit)

            session.commit()
            session.refresh(campaign)

            # Invalidate Redis hot read cache on write
            invalidate_cache("cache:campaigns:*")
            return campaign
        except Exception:
            session.rollback()
            raise

    @staticmethod
    def close_campaign(
        session: Session,
        campaign_id: int,
        actor: User,
    ) -> Campaign:
        campaign = session.get(Campaign, campaign_id)
        if not campaign:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="CAMPAIGN_NOT_FOUND",
                message=f"Campaign with ID {campaign_id} was not found.",
            )

        if campaign.status == CampaignStatus.CLOSED.value:
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                code="CAMPAIGN_ALREADY_CLOSED",
                message=f"Campaign '{campaign.title}' is already closed.",
            )

        try:
            campaign.status = CampaignStatus.CLOSED.value
            campaign.updated_at = datetime.now(timezone.utc)
            session.add(campaign)

            audit = AuditLog(
                actor_id=actor.id,
                action="CLOSE_CAMPAIGN",
                target_type="campaigns",
                target_id=campaign.id,
                details=f"Admin closed campaign '{campaign.title}'",
            )
            session.add(audit)

            session.commit()
            session.refresh(campaign)

            # Invalidate Redis cache
            invalidate_cache("cache:campaigns:*")
            return campaign
        except Exception:
            session.rollback()
            raise
