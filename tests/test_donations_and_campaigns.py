"""
tests/test_donations_and_campaigns.py
Acceptance tests for campaigns, pledges, donation recording, idempotency keys, and statements.
"""
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.domains.campaigns.models import Campaign


def test_new_bank_reference_recorded_returns_201(client: TestClient, seed_data: dict):
    """Given a new bank reference, when finance records it -> 201 and one donation row."""
    token = seed_data["finance_token"]
    campaign_id = seed_data["campaign"].id
    payload = {
        "campaign_id": campaign_id,
        "amount": 2500000,
        "bank_ref": "TXN-NEW-REF-001",
    }
    resp = client.post(
        "/api/v1/donations",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["bank_ref"] == "TXN-NEW-REF-001"


def test_same_bank_reference_returns_409_and_totals_unchanged(client: TestClient, seed_data: dict, session: Session):
    """Given a bank reference that was already recorded -> 409 and totals do not change."""
    token = seed_data["finance_token"]
    campaign = seed_data["campaign"]
    initial_raised = campaign.raised_amount

    payload = {
        "campaign_id": campaign.id,
        "amount": 4000000,
        "bank_ref": "TXN-REPEAT-REF-001",
    }

    # 1. First record -> success
    resp1 = client.post("/api/v1/donations", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp1.status_code == 201

    # Check raised balance increased
    session.refresh(campaign)
    assert campaign.raised_amount == initial_raised + 4000000

    # 2. Second record -> 409
    resp2 = client.post("/api/v1/donations", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 409
    assert resp2.json()["error"]["code"] == "DUPLICATE_BANK_REFERENCE"

    # Total must NOT have changed again
    session.refresh(campaign)
    assert campaign.raised_amount == initial_raised + 4000000


def test_idempotency_key_retried_returns_200_with_original_response(client: TestClient, seed_data: dict):
    """Given the same request is retried with the same Idempotency-Key, then 200 with the original response."""
    token = seed_data["finance_token"]
    campaign_id = seed_data["campaign"].id
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "idemp-key-uuid-999",
    }
    payload = {
        "campaign_id": campaign_id,
        "amount": 1000000,
        "bank_ref": "TXN-IDEMP-REF-001",
    }

    # 1. Initial request -> 201 Created
    resp1 = client.post("/api/v1/donations", json=payload, headers=headers)
    assert resp1.status_code == 201
    body1 = resp1.json()

    # 2. Repeated request with exact same Idempotency-Key -> 200 OK with identical payload
    resp2 = client.post("/api/v1/donations", json=payload, headers=headers)
    assert resp2.status_code == 200
    body2 = resp2.json()

    assert body1["id"] == body2["id"]
    assert body1["bank_ref"] == body2["bank_ref"]
    assert body1["amount"] == body2["amount"]


def test_recording_donation_against_closed_campaign_returns_409(client: TestClient, seed_data: dict):
    """Given a closed campaign, when recording against it -> 409 Conflict."""
    token = seed_data["finance_token"]
    closed_campaign_id = seed_data["closed_campaign"].id
    payload = {
        "campaign_id": closed_campaign_id,
        "amount": 1000000,
        "bank_ref": "TXN-CLOSED-CAMP-REF-001",
    }
    resp = client.post(
        "/api/v1/donations",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CAMPAIGN_CLOSED"


def test_donor_can_create_pledge_on_open_campaign(client: TestClient, seed_data: dict):
    """Donor can create a pledge towards an open campaign."""
    donor_token = seed_data["donor_token"]
    campaign_id = seed_data["campaign"].id
    resp = client.post(
        "/api/v1/pledges",
        json={"campaign_id": campaign_id, "amount": 15000000},
        headers={"Authorization": f"Bearer {donor_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["amount"] == 15000000
    assert resp.json()["status"] == "pending"


def test_pledge_on_closed_campaign_returns_409(client: TestClient, seed_data: dict):
    """Attempting to pledge to a closed campaign returns 409 Conflict."""
    donor_token = seed_data["donor_token"]
    closed_id = seed_data["closed_campaign"].id
    resp = client.post(
        "/api/v1/pledges",
        json={"campaign_id": closed_id, "amount": 5000000},
        headers={"Authorization": f"Bearer {donor_token}"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CAMPAIGN_CLOSED"


def test_finance_can_export_statement_report(client: TestClient, seed_data: dict):
    """Finance officer can export audit statement for a date window."""
    finance_token = seed_data["finance_token"]
    resp = client.get(
        "/api/v1/reports/statement?from=2020-01-01T00:00:00Z&to=2030-12-31T23:59:59Z",
        headers={"Authorization": f"Bearer {finance_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_donations" in data
    assert "total_amount" in data
    assert "items" in data


def test_donor_cannot_export_statement_returns_403(client: TestClient, seed_data: dict):
    """Donor attempting to export statement report receives 403 Forbidden."""
    donor_token = seed_data["donor_token"]
    resp = client.get(
        "/api/v1/reports/statement?from=2020-01-01T00:00:00Z&to=2030-12-31T23:59:59Z",
        headers={"Authorization": f"Bearer {donor_token}"},
    )
    assert resp.status_code == 403


def test_campaign_listing_and_admin_creation_and_closing(client: TestClient, seed_data: dict):
    """Tests public listing, admin creation with cache invalidation, and admin closing."""
    # 1. Public list campaigns -> 200
    resp1 = client.get("/api/v1/campaigns")
    assert resp1.status_code == 200
    assert resp1.json()["total"] >= 1

    # 2. Donor cannot create campaign -> 403
    donor_token = seed_data["donor_token"]
    resp2 = client.post(
        "/api/v1/campaigns",
        json={"title": "Unauthorized Campaign", "goal_amount": 1000000},
        headers={"Authorization": f"Bearer {donor_token}"},
    )
    assert resp2.status_code == 403

    # 3. Admin creates campaign -> 201
    admin_token = seed_data["admin_token"]
    resp3 = client.post(
        "/api/v1/campaigns",
        json={"title": "Solar Power for Clinic", "goal_amount": 80000000},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp3.status_code == 201
    camp_id = resp3.json()["id"]

    # 4. Admin closes campaign -> 200
    resp4 = client.post(
        f"/api/v1/campaigns/{camp_id}/close",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp4.status_code == 200
    assert resp4.json()["status"] == "closed"

    # 5. Closing already closed campaign -> 409
    resp5 = client.post(
        f"/api/v1/campaigns/{camp_id}/close",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp5.status_code == 409
    assert resp5.json()["error"]["code"] == "CAMPAIGN_ALREADY_CLOSED"
