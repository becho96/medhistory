"""Embeddings sidecar — wraps multilingual-e5-base behind a small HTTP API.

The e5 family requires task-specific prefixes ("passage: " for stored documents,
"query: " for search queries) — that responsibility lives here so backend
callers don't need to know.
"""
import os
import logging
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

MODEL_NAME = os.environ.get("EMBEDDINGS_MODEL", "intfloat/multilingual-e5-base")
MAX_BATCH = int(os.environ.get("EMBEDDINGS_MAX_BATCH", "32"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("embeddings")

log.info(f"Loading model: {MODEL_NAME}")
model = SentenceTransformer(MODEL_NAME, device="cpu")
DIM = model.get_sentence_embedding_dimension()
log.info(f"Model ready, dimension={DIM}")

app = FastAPI(title="medhistory-embeddings")


class EmbedRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1, max_length=128)


class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    dimension: int


def _encode(texts: List[str], prefix: str) -> List[List[float]]:
    prefixed = [f"{prefix}{t}" for t in texts]
    vectors = model.encode(
        prefixed,
        batch_size=MAX_BATCH,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vectors.tolist()


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME, "dimension": DIM}


@app.post("/embed/passages", response_model=EmbedResponse)
def embed_passages(req: EmbedRequest):
    return EmbedResponse(embeddings=_encode(req.texts, "passage: "), dimension=DIM)


@app.post("/embed/queries", response_model=EmbedResponse)
def embed_queries(req: EmbedRequest):
    return EmbedResponse(embeddings=_encode(req.texts, "query: "), dimension=DIM)
