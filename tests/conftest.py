import os
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings

# Force testing environment before importing or mounting app
settings.APP_ENV = "testing"

from app.core.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.session import engine as main_engine
from app.domains.audit.models import AuditLog
from app.domains.audit.service import AuditService
from app.domains.auth.models import Member, User, UserRole
from app.domains.campaigns.models import Campaign, CampaignStatus
from app.main import app

# Isolated In-Memory SQLite Engine for high-speed, repeatable tests
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="session", scope="function")
def session_fixture():
    """Provides a clean database session per test with append-only triggers."""
    SQLModel.metadata.create_all(test_engine)
    AuditService.enforce_append_only_rules(test_engine)

    with Session(test_engine) as session:
        yield session

    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(name="client", scope="function")
def client_fixture(session: Session):
    """Overrides get_db dependency with test database session."""
    def get_test_db():
        yield session

    app.dependency_overrides[get_db] = get_test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(name="seed_data")
def seed_data_fixture(session: Session):
    """Seeds standard users (admin, finance, donor) and an open campaign for testing."""
    # 1. Admin
    admin = User(
        email="admin_test@givenaija.org",
        password_hash=hash_password("AdminPass123!"),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    session.add(admin)

    # 2. Finance Officer
    finance = User(
        email="finance_test@givenaija.org",
        password_hash=hash_password("FinancePass123!"),
        role=UserRole.FINANCE.value,
        is_active=True,
    )
    session.add(finance)

    # 3. Donor
    donor = User(
        email="donor_test@givenaija.org",
        password_hash=hash_password("DonorPass123!"),
        role=UserRole.DONOR.value,
        is_active=True,
    )
    session.add(donor)
    session.flush()

    # Member for donor
    member = Member(user_id=donor.id, phone="+2348099887766")
    session.add(member)

    # Open Campaign
    campaign = Campaign(
        title="Test Clean Water Campaign",
        description="Clean water for Ikot Ekpene",
        goal_amount=100000000,
        raised_amount=0,
        status=CampaignStatus.OPEN.value,
    )
    session.add(campaign)

    # Closed Campaign
    closed_campaign = Campaign(
        title="Test Completed Campaign",
        description="Past project",
        goal_amount=50000000,
        raised_amount=50000000,
        status=CampaignStatus.CLOSED.value,
    )
    session.add(closed_campaign)

    session.commit()
    session.refresh(admin)
    session.refresh(finance)
    session.refresh(donor)
    session.refresh(member)
    session.refresh(campaign)
    session.refresh(closed_campaign)

    admin_token = create_access_token(admin.email, admin.role, admin.id)
    finance_token = create_access_token(finance.email, finance.role, finance.id)
    donor_token = create_access_token(donor.email, donor.role, donor.id)

    return {
        "admin": admin,
        "finance": finance,
        "donor": donor,
        "member": member,
        "campaign": campaign,
        "closed_campaign": closed_campaign,
        "admin_token": admin_token,
        "finance_token": finance_token,
        "donor_token": donor_token,
    }
