from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_current_identity, Identity
from ..db.base import get_db
from ..db import crud
from ..db.schemas import SessionOut, MessageOut

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionCreateIn(BaseModel):
    title: Optional[str] = None
class SessionUpdateIn(BaseModel):
    title: Optional[str] = None



@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    body: SessionCreateIn,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    if not identity:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    if "user_id" in identity:
        sess = crud.create_user_session(db, user_id=UUID(identity["user_id"]), title=body.title)
        return SessionOut.model_validate(sess)
    anon_id = identity.get("anon_id")
    if not anon_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Anonymous identity missing")
    sess = crud.create_anon_session(db, anon_id=anon_id, title=body.title)
    return SessionOut.model_validate(sess)


@router.get("", response_model=list[SessionOut])
def list_sessions(
    limit: int = Query(50, ge=1, le=200, description="Max sessions to return"),
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    if not identity:
        return []
    if "user_id" in identity:
        rows = crud.list_sessions_for_user(db, user_id=identity["user_id"], limit=limit)
        return [SessionOut.model_validate(x) for x in rows]
    if "anon_id" in identity:
        rows = crud.list_sessions_for_anon(db, anon_id=identity["anon_id"], limit=limit)
        return [SessionOut.model_validate(x) for x in rows]
    return []


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def list_messages(
    session_id: UUID,
    limit: int = Query(50, ge=1, le=200, description="Max messages to return"),
    before: Optional[datetime] = Query(None, description="Return messages created before this ISO timestamp"),
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    if not identity:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    sess = crud.get_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if not crud.assert_session_belongs_to_identity(sess, user_id=identity.get("user_id"), anon_id=identity.get("anon_id")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if sess.deleted_at is not None:
        return []
    rows = crud.list_messages_paginated(db, session_id=session_id, limit=limit, before=before)
    return [MessageOut.model_validate(x) for x in rows]


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: UUID,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    if not identity:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    sess = crud.get_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if not crud.assert_session_belongs_to_identity(sess, user_id=identity.get("user_id"), anon_id=identity.get("anon_id")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    crud.soft_delete_session(db, session_id=session_id)
    return None


@router.patch("/{session_id}", response_model=SessionOut)
def update_session(
    session_id: UUID,
    body: SessionUpdateIn,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    if not identity:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    sess = crud.get_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if not crud.assert_session_belongs_to_identity(sess, user_id=identity.get("user_id"), anon_id=identity.get("anon_id")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if body.title is not None:
        sess = crud.update_session_title(db, session_id=session_id, title=body.title)
    return SessionOut.model_validate(sess)
