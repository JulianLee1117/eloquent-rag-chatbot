from __future__ import annotations
import uuid
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..deps import get_current_identity, Identity
from ..core.config import settings
from ..db.base import get_db
from ..db import crud
from ..db.models import Role
from ..services.chat_service import ChatService
from .sse import sse_event
from ..utils.tokens import count_tokens

router = APIRouter(prefix="/chat", tags=["chat"])

MAX_LEN = 2000  # simple guardrail

class ChatIn(BaseModel):
    session_id: Optional[UUID] = Field(default=None)
    message: str = Field(min_length=1, max_length=MAX_LEN)

def _resolve_session(db: Session, identity: Identity, session_id: Optional[UUID]) -> UUID:
    # 1) Known user → ensure session belongs to user; create if missing
    if "user_id" in identity:
        if session_id is None:
            sess = crud.create_user_session(db, user_id=uuid.UUID(identity["user_id"]))
            return sess.id
        sess = crud.get_session(db, session_id)
        if not sess or not crud.assert_session_belongs_to_identity(sess, user_id=identity["user_id"], anon_id=None):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session not found")
        return sess.id

    # 2) Anonymous → tie to anon_id; create/get if missing
    anon_id = identity.get("anon_id")
    if not anon_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Anonymous identity missing")
    if session_id is None:
        sess = crud.get_or_create_anon_session(db, anon_id=anon_id)
        return sess.id
    sess = crud.get_session(db, session_id)
    if not sess or not crud.assert_session_belongs_to_identity(sess, user_id=None, anon_id=anon_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session not found")
    return sess.id

@router.post("", response_class=StreamingResponse)
def chat_stream(body: ChatIn, request: Request, db: Session = Depends(get_db), identity: Identity = Depends(get_current_identity)):
    """
    Streams SSE frames:
      - event: token { data: "<partial text>" }
      - event: done  { data: {"citations": [], "usage": {...}, "session_id": "..."} }
    """
    if not identity:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    # Resolve/create session & persist user message up front
    sid = _resolve_session(db, identity, body.session_id)
    user_msg = crud.append_message(
        db,
        session_id=sid,
        role=Role.user,
        content=body.message,
        tokens_in=count_tokens(body.message),
    )

    # Build RAG+LLM streamer
    result = ChatService.stream_for_session(db, sid)

    # SSE generator (sync) and send an initial open frame to encourage flushing
    def event_gen():
        # headers: done below in StreamingResponse
        try:
            # initial open event to flush response headers early
            yield sse_event("open", "ok")
            # stream tokens
            for tok in result:
                # yield token events frequently
                yield sse_event("token", {"token": tok})
            # finalize & persist assistant message before signaling done
            assistant_text = "".join(result.buffer).strip()
            if assistant_text:
                crud.append_message(
                    db,
                    session_id=sid,
                    role=Role.assistant,
                    content=assistant_text,
                    tokens_in=result.usage.get("tokens_in", 0),
                    tokens_out=result.usage.get("tokens_out", 0),
                )
            # send final 'done' with metadata
            yield sse_event("done", {
                "citations": result.citations,
                "usage": result.usage,
                "session_id": str(sid),
            })
        except Exception as e:
            # minimal error channel
            yield sse_event("error", {"message": str(e)})

    # Important SSE headers: content type + keep-alive + disable proxy buffering
    # (X-Accel-Buffering helps with Nginx proxies)
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_gen(), media_type="text/event-stream", headers=headers)
