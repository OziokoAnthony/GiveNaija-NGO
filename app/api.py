from fastapi import APIRouter

from app.domains.auth.router import router as auth_router
from app.domains.campaigns.router import router as campaigns_router
from app.domains.donations.router import router as donations_router
from app.domains.donations.ledger.router import router as ledger_router
from app.domains.audit.router import router as audit_router
from app.domains.webhooks.router import router as webhooks_router

# Central API v1 router aggregating all domain sub-routers
api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(campaigns_router)
api_router.include_router(donations_router)
api_router.include_router(ledger_router)
api_router.include_router(audit_router)
api_router.include_router(webhooks_router)
