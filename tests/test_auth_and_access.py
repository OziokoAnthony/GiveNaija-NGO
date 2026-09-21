"""
tests/test_auth_and_access.py
Tests for authentication, authorization (401 vs 403), role enforcement, and rate limiting.
"""
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.domains.auth.models import User, Member


def test_no_token_returns_401(client: TestClient):
    """Accessing protected endpoints with no token returns 401 Unauthorized."""
    resp = client.get("/api/v1/admin/audit-log")
    assert resp.status_code == 401
    data = resp.json()
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_donor_token_on_audit_log_returns_403(client: TestClient, seed_data: dict):
    """Given a donor token on the audit log endpoint -> 403 Forbidden."""
    donor_token = seed_data["donor_token"]
    resp = client.get(
        "/api/v1/admin/audit-log",
        headers={"Authorization": f"Bearer {donor_token}"},
    )
    assert resp.status_code == 403
    data = resp.json()
    assert data["error"]["code"] == "FORBIDDEN"


def test_donor_registration_creates_member_profile_and_returns_201(client: TestClient, session: Session):
    """Registering a new donor account returns 201 and creates member profile."""
    payload = {
        "email": "new_donor@example.com",
        "password": "SecurePassword123!",
        "role": "donor",
        "phone": "+2347098765432",
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new_donor@example.com"
    assert "password_hash" not in data  # Never expose internal credentials

    # Verify Member table
    user = session.exec(select(User).where(User.email == "new_donor@example.com")).first()
    assert user is not None
    member = session.exec(select(Member).where(Member.user_id == user.id)).first()
    assert member is not None
    assert member.phone == "+2347098765432"


def test_duplicate_email_registration_returns_409(client: TestClient):
    """Attempting to register with an existing email returns 409 Conflict."""
    payload = {
        "email": "unique_donor@example.com",
        "password": "Password123!",
        "role": "donor",
    }
    resp1 = client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 409
    assert resp2.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_login_valid_credentials_returns_jwt_and_user(client: TestClient, seed_data: dict):
    """Valid login returns 200, JWT bearer token, and user details."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "donor_test@givenaija.org", "password": "DonorPass123!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "donor_test@givenaija.org"


def test_login_invalid_password_returns_401(client: TestClient):
    """Invalid password returns 401 Unauthorized."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "donor_test@givenaija.org", "password": "WrongPassword!"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_rate_limiting_returns_429_with_retry_after(client: TestClient):
    """Exceeding 5 login attempts within a minute returns 429 Too Many Requests + Retry-After."""
    payload = {"email": "ratelimit_test@example.com", "password": "WrongPassword!"}

    status_codes = []
    for _ in range(6):
        resp = client.post("/api/v1/auth/login", json=payload)
        status_codes.append(resp.status_code)

    assert 429 in status_codes
    assert "Retry-After" in resp.headers
    assert resp.json()["error"]["code"] == "RATE_LIMITED"
