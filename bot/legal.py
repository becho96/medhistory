"""Fetch legal documents and compute consent version hashes.

Mirrors the frontend's loadConsentVersions: each consent's document_version
is the sha256 of its (joined) markdown — the exact text the user agreed to.
"""
import hashlib

import httpx

import config


async def compute_consents() -> dict[str, str]:
    """Return {consent_type: sha256} for every entry in config.CONSENT_DEFS.

    Raises httpx.HTTPError if a document cannot be fetched.
    """
    result: dict[str, str] = {}
    async with httpx.AsyncClient(base_url=config.LEGAL_BASE_URL, timeout=20.0) as client:
        for definition in config.CONSENT_DEFS:
            texts: list[str] = []
            for doc in definition["docs"]:
                response = await client.get(doc["path"])
                response.raise_for_status()
                texts.append(response.text)
            joined = config.CONSENT_JOIN.join(texts)
            result[definition["key"]] = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return result
