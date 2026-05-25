"""Short-lived signed tokens for one-off document downloads.

Used by the MCP `get_document_original` tool to hand an LLM (or any external
client) a self-contained URL that does not require Bearer auth. The token is a
JWT signed with the same secret as access tokens but carries `typ=doc_download`
so it cannot be used in place of a session token (and vice versa).
"""
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt

from app.core.config import settings

DOWNLOAD_TOKEN_TYPE = "doc_download"


def create_download_token(
    user_id: str,
    document_id: str,
    expires_in_seconds: int = 300,
) -> str:
    payload = {
        "sub": str(user_id),
        "doc": str(document_id),
        "typ": DOWNLOAD_TOKEN_TYPE,
        "exp": datetime.utcnow() + timedelta(seconds=expires_in_seconds),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_download_token(token: str, expected_document_id: str) -> Optional[str]:
    """Return user_id if the token is valid for `expected_document_id`, else None."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None

    if payload.get("typ") != DOWNLOAD_TOKEN_TYPE:
        return None
    if str(payload.get("doc")) != str(expected_document_id):
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None
    return str(user_id)
