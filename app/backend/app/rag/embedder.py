from __future__ import annotations
import logging
from pinecone import Pinecone
from ..core.config import settings


_pc = Pinecone(api_key=settings.pinecone_api_key)
MODEL = settings.embedding_model or "llama-text-embed-v2"
logger = logging.getLogger("rag.embedder")


def embed_query(text: str) -> list[float]:
    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY missing")
    out = _pc.inference.embed(
        model=MODEL,
        inputs=[text],
        parameters={"input_type": "query", "truncate": "END"},
    )
    vec = list(out.data[0].values)
    try:
        l2 = sum(v * v for v in vec) ** 0.5
    except Exception:
        l2 = -1.0
    logger.debug(
        "embed_query: model=%s dim=%d l2=%.4f text_preview=%s",
        MODEL,
        len(vec),
        l2,
        text[:80],
    )
    return vec


