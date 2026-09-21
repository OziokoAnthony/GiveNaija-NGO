"""
tests/test_ledger.py — Comprehensive tests for the financial ledger sub-domain.
Validates campaign ledger access, role boundaries, donor payment history,
reconciliation verification, and automatic ledger entry creation on donations.
"""
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.domains.campaigns.models import Campaign
from app.domains.donations.ledger.models import LedgerEntry, EntryType


def test_finance_can_view_campaign_ledger(client: TestClient, seed_data: dict, session: Session):
    """Given a campaign with donations, finance officer can view all ledger entries."""
    finance_token = seed_data["finance_token"]
    campaign = seed_data["campaign"]

    # Record a donation through the API
    payload = {
        "campaign_id": campaign.id,
        "amount": 1000000,  # 10,000 NGN
        "bank_ref": "TXN-LEDGER-001",
    }
    create_resp = client.post(
        "/api/v1/donations",
        json=payload,
        headers={"Authorization": f"Bearer {finance_token}"},
    )
    assert create_resp.status_code == 201

    # Query campaign ledger
    resp = client.get(
        f"/api/v1/ledger/campaign/{campaign.id}",
        headers={"Authorization": f"Bearer {finance_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["campaign_id"] == campaign.id
    assert data["count"] >= 1
    assert any(e["amount_ngn"] == "10000.00" for e in data["entries"])


def test_donor_cannot_view_campaign_ledger(client: TestClient, seed_data: dict):
    """Given an authenticated donor, accessing the campaign ledger is rejected with 403."""
    donor_token = seed_data["donor_token"]
    campaign = seed_data["campaign"]

    resp = client.get(
        f"/api/v1/ledger/campaign/{campaign.id}",
        headers={"Authorization": f"Bearer {donor_token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_donor_can_view_personal_payment_history(client: TestClient, seed_data: dict):
    """Given an authenticated donor, they can view their own payment history via /ledger/me."""
    donor_token = seed_data["donor_token"]

    resp = client.get(
        "/api/v1/ledger/me",
        headers={"Authorization": f"Bearer {donor_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "donor_id" in data
    assert "entries" in data
    assert isinstance(data["entries"], list)


def test_admin_reconcile_campaign_ledger_match(client: TestClient, seed_data: dict, session: Session):
    """Admin can trigger ledger verification to reconcile ledger rows against raised_amount."""
    admin_token = seed_data["admin_token"]
    finance_token = seed_data["finance_token"]
    campaign = seed_data["campaign"]

    # Record a known donation
    client.post(
        "/api/v1/donations",
        json={
            "campaign_id": campaign.id,
            "amount": 5000000,  # 50,000 NGN
            "bank_ref": "TXN-RECONCILE-001",
        },
        headers={"Authorization": f"Bearer {finance_token}"},
    )

    # Reconcile via admin endpoint
    resp = client.get(
        f"/api/v1/ledger/campaign/{campaign.id}/verify",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["match"] is True
    assert data["status"] == "OK"
    assert Decimal(data["ledger_total_ngn"]) > Decimal("0")


def test_donation_automatically_creates_ledger_entry(client: TestClient, seed_data: dict, session: Session):
    """Recording a donation MUST create a corresponding LedgerEntry row inside the same transaction."""
    finance_token = seed_data["finance_token"]
    campaign = seed_data["campaign"]

    bank_ref = "TXN-AUTO-LEDGER-999"
    resp = client.post(
        "/api/v1/donations",
        json={
            "campaign_id": campaign.id,
            "amount": 7500000,  # 75,000 NGN
            "bank_ref": bank_ref,
        },
        headers={"Authorization": f"Bearer {finance_token}"},
    )
    assert resp.status_code == 201
    donation_id = resp.json()["id"]

    # Directly check database for the ledger entry
    entry = session.exec(
        select(LedgerEntry).where(LedgerEntry.donation_id == donation_id)
    ).first()

    assert entry is not None
    assert entry.campaign_id == campaign.id
    assert entry.entry_type == EntryType.CREDIT
    assert entry.amount_ngn == Decimal("75000.00")
