"""Thin async HTTP client for the embeddings sidecar.

The sidecar adds the e5-family task prefixes ("passage: " / "query: ")
internally, so callers just pass plain text.
"""
from typing import List
import logging

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


class EmbeddingsError(RuntimeError):
    pass


async def _post(path: str, texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    url = f"{settings.EMBEDDINGS_URL.rstrip('/')}{path}"
    async with httpx.AsyncClient(timeout=settings.EMBEDDINGS_TIMEOUT) as client:
        try:
            resp = await client.post(url, json={"texts": texts})
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise EmbeddingsError(f"Embeddings sidecar request failed: {e}") from e
    data = resp.json()
    return data["embeddings"]


async def embed_passages(texts: List[str]) -> List[List[float]]:
    """Encode stored documents (summaries, paragraphs) for indexing."""
    return await _post("/embed/passages", texts)


async def embed_query(text: str) -> List[float]:
    """Encode a user search query for retrieval."""
    vectors = await _post("/embed/queries", [text])
    return vectors[0]
