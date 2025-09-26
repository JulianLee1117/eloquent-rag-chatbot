from __future__ import annotations
from collections.abc import Iterator
import logging
from typing import Iterable, List, Tuple
from sqlalchemy.orm import Session
from ..core.config import settings
from ..db import crud
from ..db.models import Role
from .embedder import embed_query
from .retriever import retrieve_optimal
from .prompt import build_messages
from .types import Doc
from ..llm.client import get_openai

MAX_CONTEXT_MESSAGES = 12
RETRIEVE_TOP_K = 10
FINAL_CONTEXT_K = 4

logger = logging.getLogger("rag.pipeline")

class StreamResult:
    def __init__(self, tokens: Iterable[str], *, citations: list[dict], tokens_in: int = 0):
        self._tokens = iter(tokens)
        self.buffer: List[str] = []
        self.citations = citations
        self.usage = {"tokens_in": tokens_in, "tokens_out": 0}

    def __iter__(self) -> Iterator[str]:
        for tok in self._tokens:
            self.buffer.append(tok)
            yield tok
        self.usage["tokens_out"] = sum(len(t.split()) for t in self.buffer)


def _history_and_latest_user(db: Session, session_id) -> Tuple[list[dict], str]:
    rows = crud.list_messages(db, session_id=session_id, limit=MAX_CONTEXT_MESSAGES)
    # Ensure we pick the most recent user message for embedding
    rows_sorted = sorted(rows, key=lambda r: r.created_at)
    history: list[dict] = []
    latest_user = ""
    for r in rows_sorted:
        if r.role == Role.user:
            latest_user = r.content
            history.append({"role": "user", "content": r.content})
        elif r.role == Role.assistant:
            history.append({"role": "assistant", "content": r.content})
    if not latest_user and rows_sorted:
        # fallback to the last message content if no user messages present
        latest_user = rows_sorted[-1].content
    logger.debug("history_and_latest_user: messages=%d latest_user_preview=%s", len(rows_sorted), latest_user[:80] if latest_user else "")
    return history, latest_user


def _select_context(query: str) -> List[Doc]:
    docs = retrieve_optimal(query_text=query, final_k=FINAL_CONTEXT_K)
    logger.debug(
        "select_context: query_preview=%s selected=%s",
        query[:80],
        [(d.id, round(d.score, 4), d.category) for d in docs],
    )
    return docs


def generate_stream_for_session(db: Session, session_id: str) -> StreamResult:
    history, user_q = _history_and_latest_user(db, session_id)
    if not user_q:
        user_q = "Respond helpfully based on the context."
    docs = _select_context(user_q)
    citations = [d.to_citation(i + 1) for i, d in enumerate(docs)]
    messages = build_messages(history, user_q, docs)
    logger.debug("generate_stream: user_q_preview=%s citations=%s", user_q[:80], citations)

    client = get_openai()
    model = settings.llm_model or "gpt-4o-mini"
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        stream=True,
    )

    def _token_iter():
        tokens_in = 0
        for m in messages:
            tokens_in += len(str(m.get("content", "")).split())
        for chunk in stream:
            choice = chunk.choices[0]
            delta = getattr(choice, "delta", None)
            if delta and getattr(delta, "content", None):
                yield delta.content

    return StreamResult(_token_iter(), citations=citations)
