from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.middleware import RateLimiterMiddleware, RequestLoggingAndTimingMiddleware
from app.db.session import engine, init_db
from app.domains.audit.service import AuditService

# Import all models via central model registry
import app.db.base  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown events.
    Ensures tables, migrations, and DB triggers are initialized for live execution.
    In testing mode, tests manage their own isolated test database fixtures.
    """
    if settings.APP_ENV != "testing":
        try:
            init_db()
            AuditService.enforce_append_only_rules(engine)
            try:
                from app.db.migrations import run_migrations
                run_migrations()
            except Exception as mig_err:
                print(f"Notice on auto-migration: {mig_err}")
        except Exception as e:
            print(f"Notice on live database setup: {e}")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "**GiveNaija — NGO Donations & Members API**\n\n"
        "Capstone Project by Team Mighty Spark (Victor & Anthony).\n\n"
        "Guarantees:\n"
        "- **Exactly Once**: Every bank reference recorded exactly once via UNIQUE constraints and Idempotency-Key.\n"
        "- **Unalterable Audit Trail**: Append-only audit logs enforced at the database level.\n"
        "- **Performance**: Redis caching with invalidation on write.\n"
        "- **Real-time**: Live Server-Sent Events (SSE) donation ticker."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 1. Register Uniform Error Handlers
register_exception_handlers(app)

# 2. Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Add Request ID, Logging, and Timing Middleware
app.add_middleware(RequestLoggingAndTimingMiddleware)

# 4. Add Rate Limiting Middleware (429 + Retry-After)
app.add_middleware(RateLimiterMiddleware)

# 5. Register All API v1 Routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def root():
    """Redirect root access directly to interactive Swagger OpenAPI documentation."""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for container orchestrators and monitoring probes."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }
