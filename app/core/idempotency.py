"""
app/core/idempotency.py — Reusable idempotency guard.

Any endpoint that must be safe to retry (POST /donations, webhooks, etc.)
imports check_idempotency_key() and store_idempotency_response() from here.

Flow:
    1. Client sends   POST /donations  with  Idempotency-Key: <uuid>
    2. check_idempotency_key() returns the stored response if the key exists
       → caller immediately returns HTTP 200 with the original body (no re-processing)
    3. If the key is new, the caller processes normally, then calls
       store_idempotency_response() to save the result for future replays.

Why here?
    Idempotency is a cross-cutting concern (auth, donations, webhooks all need it).
    Keeping it in app/core/ means no domain imports another domain.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from app.domains.donations.models import IdempotencyRecord


def check_idempotency_key(
    session: Session,
    key: str,
) -> dict[str, Any] | None:
    """
    Look up an idempotency key in the database.

    Returns the original response dict if the key was seen before,
    or None if this is a brand-new key.

    Args:
        session: Active SQLModel database session.
        key:     The idempotency key string from the request header.

    Returns:
        Parsed response dict (from JSON) on replay, None on first call.
    """
    # SELECT * FROM idempotency_keys WHERE key = :key LIMIT 1
    record = session.exec(
        select(IdempotencyRecord).where(IdempotencyRecord.key == key)
    ).first()

    if record is None:
        return None  # First time we have seen this key — process normally

    # Key already exists — return the stored response body verbatim
    return json.loads(record.response_json)


def store_idempotency_response(
    session: Session,
    key: str,
    response_data: dict[str, Any],
) -> None:
    """
    Persist an idempotency key and its response body so future retries
    with the same key get the same response without re-processing.

    Must be called INSIDE the same transaction as the main operation so
    both commit or both roll back atomically.

    Args:
        session:       Active SQLModel database session.
        key:           The idempotency key string from the request header.
        response_data: The response dict that was returned to the client.
    """
    record = IdempotencyRecord(
        key=key,
        response_json=json.dumps(response_data),
        created_at=datetime.now(timezone.utc),
    )
    session.add(record)
    # NOTE: Do NOT call session.commit() here.
    # The caller owns the transaction boundary.
