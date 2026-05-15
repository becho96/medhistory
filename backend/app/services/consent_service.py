"""Recording of 152-ФЗ consent grants.

Shared by web registration and the Telegram bot so consent rows are written
identically regardless of the channel the user signed up through.
"""
from typing import Iterable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent import UserConsent
from app.models.user import User


def record_consents(
    db: AsyncSession,
    user: User,
    consents: dict[str, str],
    *,
    ip_address: Optional[str],
    user_agent: Optional[str],
    only_types: Optional[Iterable[str]] = None,
) -> None:
    """Stage UserConsent rows for a user.

    Each value in `consents` is the sha256 of the legal document the user saw.
    When `only_types` is given, consent types outside that set are ignored;
    otherwise every supplied consent is recorded. The caller commits.
    """
    allowed = set(only_types) if only_types is not None else None
    for consent_type, document_version in consents.items():
        if allowed is not None and consent_type not in allowed:
            continue
        db.add(UserConsent(
            user_id=user.id,
            consent_type=consent_type,
            document_version=document_version,
            ip_address=ip_address,
            user_agent=user_agent,
        ))
