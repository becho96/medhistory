"""In-memory store for pending consent requests.

Lifecycle: created in `provider.authorize()`, consumed by the consent endpoint
once the user approves. Entries TTL = 10 min; expired ones are swept lazily.

Single-instance only — when we go multi-instance, swap for Redis.
"""
import time
from dataclasses import dataclass
from typing import Optional

PENDING_TTL_SECONDS = 600


@dataclass
class PendingConsent:
    client_id: str
    scopes: list[str]
    code_challenge: str
    redirect_uri: str
    redirect_uri_provided_explicitly: bool
    state: Optional[str]
    resource: Optional[str]
    expires_at: float


_store: dict[str, PendingConsent] = {}


def put(req_id: str, item: PendingConsent) -> None:
    _sweep()
    _store[req_id] = item


def take(req_id: str) -> Optional[PendingConsent]:
    """One-shot read: removes the entry on retrieval."""
    _sweep()
    item = _store.pop(req_id, None)
    if item is None or item.expires_at < time.time():
        return None
    return item


def peek(req_id: str) -> Optional[PendingConsent]:
    _sweep()
    item = _store.get(req_id)
    if item is None or item.expires_at < time.time():
        return None
    return item


def _sweep() -> None:
    now = time.time()
    expired = [k for k, v in _store.items() if v.expires_at < now]
    for k in expired:
        _store.pop(k, None)
