import asyncio
from datetime import datetime, timezone
import json
from typing import AsyncGenerator, Dict, List

# In-memory subscriber queues for SSE streams per campaign_id
_subscribers: Dict[int, List[asyncio.Queue]] = {}
_lock = asyncio.Lock()


async def register_campaign_subscriber(campaign_id: int) -> asyncio.Queue:
    """Register an SSE client queue for a specific campaign stream."""
    queue: asyncio.Queue = asyncio.Queue()
    async with _lock:
        if campaign_id not in _subscribers:
            _subscribers[campaign_id] = []
        _subscribers[campaign_id].append(queue)
    return queue


async def unregister_campaign_subscriber(campaign_id: int, queue: asyncio.Queue) -> None:
    """Unregister an SSE client queue when the connection closes."""
    async with _lock:
        if campaign_id in _subscribers and queue in _subscribers[campaign_id]:
            _subscribers[campaign_id].remove(queue)
            if not _subscribers[campaign_id]:
                del _subscribers[campaign_id]


async def broadcast_donation_event(campaign_id: int, event_payload: dict) -> None:
    """
    Broadcasts a new donation event to all active SSE subscribers for this campaign.
    Format: {"type": "donation.recorded", "id": ..., "data": event_payload, "at": ...}
    """
    async with _lock:
        queues = list(_subscribers.get(campaign_id, []))

    envelope = {
        "type": "donation.recorded",
        "id": f"evt_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
        "data": event_payload,
        "at": datetime.now(timezone.utc).isoformat(),
    }

    for q in queues:
        await q.put(envelope)
