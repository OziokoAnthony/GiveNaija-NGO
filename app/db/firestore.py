import logging
from datetime import datetime, timezone
from typing import Any, Dict
from app.core.config import settings

logger = logging.getLogger(__name__)

# Firestore client initialization with fallback
firestore_client = None
try:
    from google.cloud import firestore
    firestore_client = firestore.Client(project=settings.FIRESTORE_PROJECT_ID)
except Exception as e:
    logger.info(f"Firestore running in local simulation mode ({e})")


def sync_donation_to_feed(campaign_id: int, donation_data: Dict[str, Any]) -> None:
    """
    Pushes donation to Firestore collection: donation_feed/{campaign_id}.
    Provides high-concurrency public feeds without stressing primary OLTP Postgres.
    """
    if not firestore_client:
        logger.info(f"[Firestore Sim] Pushed to donation_feed/{campaign_id}: {donation_data}")
        return
    try:
        doc_ref = firestore_client.collection("donation_feed").document(str(campaign_id))
        doc_ref.collection("donations").add({
            **donation_data,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.error(f"Failed to sync donation to Firestore feed: {e}")


def sync_activity_to_feed(activity_data: Dict[str, Any]) -> None:
    """
    Pushes staff/admin actions to Firestore: activity_feed.
    """
    if not firestore_client:
        logger.info(f"[Firestore Sim] Pushed to activity_feed: {activity_data}")
        return
    try:
        firestore_client.collection("activity_feed").add({
            **activity_data,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.error(f"Failed to sync activity to Firestore: {e}")
