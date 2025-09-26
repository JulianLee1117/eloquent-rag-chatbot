from __future__ import annotations
from collections.abc import Iterator
from typing import Iterable, List, Tuple
import logging

from sqlalchemy.orm import Session

from ..core.config import settings
from ..db import crud
from ..db.models import Role
from ..rag.retriever import retrieve_optimal
from ..rag.prompt import build_messages
from ..rag.types import Doc
from ..llm.client import get_openai
from ..utils.tokens import count_tokens


logger = logging.getLogger("services.chat")


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
        # Post-hoc approximate token count for output using model tokenizer
        text = "".join(self.buffer)
        self.usage["tokens_out"] = count_tokens(text)


class ChatService:
    MAX_CONTEXT_MESSAGES = 12
    FINAL_CONTEXT_K = 4

    @staticmethod
    def _build_context_window(db: Session, session_id) -> Tuple[list[dict], str]:
        rows = crud.list_messages(db, session_id=session_id, limit=ChatService.MAX_CONTEXT_MESSAGES)
        history: list[dict] = []
        latest_user = ""
        for r in rows:
            if r.role == Role.user:
                latest_user = r.content
                history.append({"role": "user", "content": r.content})
            elif r.role == Role.assistant:
                history.append({"role": "assistant", "content": r.content})
        if not latest_user and rows:
            latest_user = rows[-1].content
        logger.debug(
            "build_context_window: messages=%d latest_user_preview=%s",
            len(rows),
            latest_user[:80] if latest_user else "",
        )
        return history, latest_user

    @staticmethod
    def _select_context(query: str) -> List[Doc]:
        docs = retrieve_optimal(query_text=query, final_k=ChatService.FINAL_CONTEXT_K)
        logger.debug(
            "select_context: query_preview=%s selected=%s",
            query[:80],
            [(d.id, round(d.score, 4), d.category) for d in docs],
        )
        return docs

    @staticmethod
    def stream_for_session(db: Session, session_id: str) -> StreamResult:
        history, user_q = ChatService._build_context_window(db, session_id)
        if not user_q:
            user_q = "Respond helpfully based on the context."
        docs = ChatService._select_context(user_q)
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

        # Precompute prompt token usage across system/context/history/user
        prompt_tokens = 0
        for m in messages:
            prompt_tokens += count_tokens(str(m.get("content", "")))

        def _token_iter():
            for chunk in stream:
                choice = chunk.choices[0]
                delta = getattr(choice, "delta", None)
                if delta and getattr(delta, "content", None):
                    yield delta.content

        return StreamResult(_token_iter(), citations=citations, tokens_in=prompt_tokens)


