"""
tests/test_hard_problem.py
The five mandatory tests for The Hard Problem:
"Exactly once, and an audit trail that cannot be edited."
"""
import concurrent.futures
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, select

from app.domains.audit.models import AuditLog
from app.domains.campaigns.models import Campaign
from app.domains.donations.models import Donation, Receipt


def test_recording_bank_reference_twice_returns_one_donation_and_409_second_time(client: TestClient, seed_data: dict, session: Session):
    """
    Hard Problem Test 1:
    Recording a bank reference twice -> one donation row and a 409 the second time.
    """
    token = seed_data["finance_token"]
    campaign_id = seed_data["campaign"].id
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "campaign_id": campaign_id,
        "amount": 2000000,
        "bank_ref": "TXN-GTB-HARD-001",
    }

    # 1. First record -> 201 Created
    resp1 = client.post("/api/v1/donations", json=payload, headers=headers)
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert data1["bank_ref"] == "TXN-GTB-HARD-001"

    # 2. Second record with same bank_ref -> 409 Conflict
    resp2 = client.post("/api/v1/donations", json=payload, headers=headers)
    assert resp2.status_code == 409
    error = resp2.json()["error"]
    assert error["code"] == "DUPLICATE_BANK_REFERENCE"

    # Verify exactly one donation exists in the database
    donations = session.exec(select(Donation).where(Donation.bank_ref == "TXN-GTB-HARD-001")).all()
    assert len(donations) == 1


def test_two_officers_recording_same_reference_at_same_time_exactly_one_succeeds(client: TestClient, seed_data: dict, session: Session):
    """
    Hard Problem Test 2:
    Two officers recording the same reference at the same time -> exactly one succeeds.
    """
    token = seed_data["finance_token"]
    campaign_id = seed_data["campaign"].id
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "campaign_id": campaign_id,
        "amount": 3000000,
        "bank_ref": "TXN-CONCURRENT-RACE-001",
    }

    results = []

    def make_request():
        return client.post("/api/v1/donations", json=payload, headers=headers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(make_request)
        f2 = executor.submit(make_request)
        results = [f1.result(), f2.result()]

    status_codes = [r.status_code for r in results]
    # Exactly one 201 and one 409 (or if idempotency key is not used, exactly one succeeds)
    assert 201 in status_codes
    assert 409 in status_codes
    assert len([s for s in status_codes if s == 201]) == 1

    # Verify database state has exactly 1 row
    donations = session.exec(select(Donation).where(Donation.bank_ref == "TXN-CONCURRENT-RACE-001")).all()
    assert len(donations) == 1


def test_every_admin_or_finance_change_adds_exactly_one_audit_log_row(client: TestClient, seed_data: dict, session: Session):
    """
    Hard Problem Test 3:
    Every admin/finance change adds exactly one audit_log row in the same transaction.
    """
    admin_token = seed_data["admin_token"]
    finance_token = seed_data["finance_token"]
    campaign_id = seed_data["campaign"].id

    initial_audit_count = len(session.exec(select(AuditLog)).all())

    # 1. Admin creates campaign -> exactly +1 audit row
    resp1 = client.post(
        "/api/v1/campaigns",
        json={"title": "Audit Test Campaign", "goal_amount": 10000000},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp1.status_code == 201
    count_after_create = len(session.exec(select(AuditLog)).all())
    assert count_after_create == initial_audit_count + 1

    # 2. Finance records donation -> exactly +1 audit row
    resp2 = client.post(
        "/api/v1/donations",
        json={"campaign_id": campaign_id, "amount": 1500000, "bank_ref": "TXN-AUDIT-CHECK-001"},
        headers={"Authorization": f"Bearer {finance_token}"},
    )
    assert resp2.status_code == 201
    count_after_donation = len(session.exec(select(AuditLog)).all())
    assert count_after_donation == count_after_create + 1

    # 3. Admin closes campaign -> exactly +1 audit row
    created_camp_id = resp1.json()["id"]
    resp3 = client.post(
        f"/api/v1/campaigns/{created_camp_id}/close",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp3.status_code == 200
    count_after_close = len(session.exec(select(AuditLog)).all())
    assert count_after_close == count_after_donation + 1


def test_update_or_delete_on_audit_log_fails_at_database_level(session: Session):
    """
    Hard Problem Test 4:
    UPDATE or DELETE on audit_log fails at the database level.
    """
    # Insert a valid audit log row
    entry = AuditLog(
        actor_id=None,
        action="TEST_LOG_ACTION",
        target_type="system",
        target_id=1,
        details="Attempting to tamper with this",
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)

    # 1. Attempting UPDATE via SQL should fail at the database level
    with pytest.raises(Exception):
        session.exec(
            text(f"UPDATE audit_log SET details = 'HACKED' WHERE id = {entry.id}")
        )
        session.commit()
    session.rollback()

    # 2. Attempting DELETE via SQL should fail at the database level
    with pytest.raises(Exception):
        session.exec(
            text(f"DELETE FROM audit_log WHERE id = {entry.id}")
        )
        session.commit()
    session.rollback()

    # Verify record still exists unchanged
    fresh = session.get(AuditLog, entry.id)
    assert fresh is not None
    assert fresh.details == "Attempting to tamper with this"


def test_requesting_receipt_twice_returns_same_receipt_number(client: TestClient, seed_data: dict):
    """
    Hard Problem Test 5:
    Requesting a receipt twice returns the same receipt number — never two.
    """
    finance_token = seed_data["finance_token"]
    headers = {"Authorization": f"Bearer {finance_token}"}
    campaign_id = seed_data["campaign"].id

    # Record donation
    donation_resp = client.post(
        "/api/v1/donations",
        json={"campaign_id": campaign_id, "amount": 5000000, "bank_ref": "TXN-RECEIPT-TEST-001"},
        headers=headers,
    )
    assert donation_resp.status_code == 201
    donation_id = donation_resp.json()["id"]

    # Request receipt 1st time
    r1 = client.get(f"/api/v1/receipts/{donation_id}", headers=headers)
    assert r1.status_code == 200
    receipt1 = r1.json()

    # Request receipt 2nd time
    r2 = client.get(f"/api/v1/receipts/{donation_id}", headers=headers)
    assert r2.status_code == 200
    receipt2 = r2.json()

    # Assert exact identity
    assert receipt1["id"] == receipt2["id"]
    assert receipt1["number"] == receipt2["number"]
    assert receipt1["number"].startswith("RCPT-")
