"""
tests/test_webhooks_and_stream.py
Tests for payment provider webhooks (HMAC-SHA256, replay protection, orphan logging)
and live Server-Sent Events (SSE) donation streaming.
"""
import asyncio
import hashlib
import hmac
import json
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.broadcaster import broadcast_donation_event, register_campaign_subscriber, unregister_campaign_subscriber
from app.core.config import settings
from app.domains.audit.models import AuditLog
from app.domains.donations.models import Donation
from app.domains.webhooks.models import ProcessedEvent


def sign_payload(body: dict, secret: str) -> tuple[bytes, str]:
    """Computes exact HMAC-SHA256 signature matching mock_payment_provider.py."""
    raw = json.dumps(body, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    return raw, sig


def test_signed_webhook_returns_200_and_records_donation_and_audit(client: TestClient, seed_data: dict, session: Session):
    """Given a signed webhook, then 200 and one donation row plus one audit row."""
    campaign_id = seed_data["campaign"].id
    event_body = {
        "event_id": "evt_valid_12345",
        "type": "payment.succeeded",
        "reference": f"CAMP-{campaign_id}",
        "amount": 7500000,
        "currency": "NGN",
        "paid_at": "2026-09-21T11:00:00Z",
    }
    raw, sig = sign_payload(event_body, settings.WEBHOOK_SECRET)

    resp = client.post(
        "/api/v1/webhooks/payment",
        content=raw,
        headers={"Content-Type": "application/json", "X-Signature": sig},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "payment_confirmed"

    # Verify donation row inserted
    donation = session.exec(select(Donation).where(Donation.bank_ref == f"CAMP-{campaign_id}")).first()
    assert donation is not None
    assert donation.amount == 7500000

    # Verify audit log row inserted
    audit = session.exec(select(AuditLog).where(AuditLog.action == "WEBHOOK_DONATION_RECORDED")).first()
    assert audit is not None


def test_same_webhook_event_again_returns_200_and_no_change(client: TestClient, seed_data: dict, session: Session):
    """Given the same event again, then 200 and no change (Idempotent webhook)."""
    campaign_id = seed_data["campaign"].id
    event_body = {
        "event_id": "evt_duplicate_67890",
        "type": "payment.succeeded",
        "reference": f"CAMP-{campaign_id}",
        "amount": 2500000,
        "currency": "NGN",
        "paid_at": "2026-09-21T11:00:00Z",
    }
    raw, sig = sign_payload(event_body, settings.WEBHOOK_SECRET)

    # 1. First delivery
    resp1 = client.post(
        "/api/v1/webhooks/payment",
        content=raw,
        headers={"Content-Type": "application/json", "X-Signature": sig},
    )
    assert resp1.status_code == 200

    count_processed = len(session.exec(select(ProcessedEvent).where(ProcessedEvent.event_id == "evt_duplicate_67890")).all())
    assert count_processed == 1

    # 2. Re-send (Retry from payment provider)
    resp2 = client.post(
        "/api/v1/webhooks/payment",
        content=raw,
        headers={"Content-Type": "application/json", "X-Signature": sig},
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "duplicate_ignored"

    # Total processed count must still be exactly 1
    count_after_retry = len(session.exec(select(ProcessedEvent).where(ProcessedEvent.event_id == "evt_duplicate_67890")).all())
    assert count_after_retry == 1


def test_webhook_bad_signature_returns_401(client: TestClient):
    """Given a bad signature, then 401 Unauthorized."""
    event_body = {
        "event_id": "evt_bad_sig_111",
        "type": "payment.succeeded",
        "reference": "CAMP-1",
        "amount": 10000,
        "currency": "NGN",
        "paid_at": "2026-09-21T11:00:00Z",
    }
    raw, _ = sign_payload(event_body, "wrong_secret")
    fake_sig = "deadbeef" * 8

    resp = client.post(
        "/api/v1/webhooks/payment",
        content=raw,
        headers={"Content-Type": "application/json", "X-Signature": fake_sig},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_webhook_unknown_reference_returns_200_and_logged_as_orphan(client: TestClient, session: Session):
    """Given an unknown reference, then 200 but logged as an orphan."""
    event_body = {
        "event_id": "evt_orphan_99999",
        "type": "payment.succeeded",
        "reference": "REF-DOES-NOT-EXIST",
        "amount": 3000000,
        "currency": "NGN",
        "paid_at": "2026-09-21T11:00:00Z",
    }
    raw, sig = sign_payload(event_body, settings.WEBHOOK_SECRET)

    resp = client.post(
        "/api/v1/webhooks/payment",
        content=raw,
        headers={"Content-Type": "application/json", "X-Signature": sig},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "orphan_logged"

    # Verify orphan recorded in processed_events table
    orphan_event = session.exec(select(ProcessedEvent).where(ProcessedEvent.event_id == "evt_orphan_99999")).first()
    assert orphan_event is not None
    assert orphan_event.is_orphan is True

    # Verify audit trail contains orphan record
    orphan_audit = session.exec(select(AuditLog).where(AuditLog.action == "ORPHAN_WEBHOOK_RECORDED")).first()
    assert orphan_audit is not None


@pytest.mark.asyncio
async def test_donation_is_broadcast_to_campaign_stream():
    """
    Given a donation is recorded, then every open campaign stream receives it within one second.
    Directly tests the async broadcaster and event delivery pipeline.
    """
    campaign_id = 42
    queue = await register_campaign_subscriber(campaign_id)

    test_payload = {
        "id": 101,
        "campaign_id": campaign_id,
        "amount": 2000000,
        "bank_ref": "TXN-STREAM-TEST",
    }

    try:
        # Trigger broadcast
        await broadcast_donation_event(campaign_id=campaign_id, event_payload=test_payload)

        # Receive from subscriber queue within 1 second
        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert event["type"] == "donation.recorded"
        assert event["data"]["amount"] == 2000000
        assert event["data"]["bank_ref"] == "TXN-STREAM-TEST"
    finally:
        await unregister_campaign_subscriber(campaign_id, queue)
