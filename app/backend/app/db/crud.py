import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import Session
from .models import User, Session as ChatSession, Message, Role

# Users
def create_user(db: Session, email: str, hashed_password: str) -> User:
    user = User(email=email, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))

# Sessions (anonymous or user-owned)
def get_or_create_anon_session(db: Session, anon_id: str, title: str | None = None) -> ChatSession:
    sess = db.scalar(
        select(ChatSession).where(ChatSession.anon_id == anon_id).order_by(ChatSession.created_at.desc())
    )
    if sess:
        return sess
    sess = ChatSession(anon_id=anon_id, title=title)
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess

def create_user_session(db: Session, user_id: uuid.UUID, title: str | None = None) -> ChatSession:
    sess = ChatSession(user_id=user_id, title=title)
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess

# Messages
def append_message(
    db: Session,
    session_id: uuid.UUID,
    role: Role,
    content: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
) -> Message:
    msg = Message(
        session_id=session_id,
        role=role,
        content=content,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

def list_messages(db: Session, session_id: uuid.UUID, limit: int = 100) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    return list(db.scalars(stmt))

def get_session(db: Session, session_id: UUID) -> ChatSession | None:
    return db.scalar(select(ChatSession).where(ChatSession.id == session_id))

def assert_session_belongs_to_identity(sess: ChatSession, *, user_id: str | None, anon_id: str | None) -> bool:
    if user_id:
        return str(sess.user_id) == user_id
    if anon_id:
        return sess.anon_id == anon_id
    return False

# --- Step 9 additions ---
def create_anon_session(db: Session, *, anon_id: str, title: str | None = None) -> ChatSession:
    sess = ChatSession(anon_id=anon_id, title=title)
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess

def list_sessions_for_user(db: Session, *, user_id: str, limit: int = 50) -> list[ChatSession]:
    stmt = (
        select(ChatSession)
        .where(and_(ChatSession.user_id == user_id, ChatSession.deleted_at.is_(None)))
        .order_by(desc(ChatSession.created_at), desc(ChatSession.id))
        .limit(limit)
    )
    return list(db.scalars(stmt))

def list_sessions_for_anon(db: Session, *, anon_id: str, limit: int = 50) -> list[ChatSession]:
    stmt = (
        select(ChatSession)
        .where(and_(ChatSession.anon_id == anon_id, ChatSession.deleted_at.is_(None)))
        .order_by(desc(ChatSession.created_at), desc(ChatSession.id))
        .limit(limit)
    )
    return list(db.scalars(stmt))

def soft_delete_session(db: Session, *, session_id: UUID) -> None:
    sess = db.get(ChatSession, session_id)
    if not sess or sess.deleted_at is not None:
        return
    sess.deleted_at = datetime.now(timezone.utc)
    db.add(sess)
    db.commit()

def list_messages_paginated(
    db: Session,
    *,
    session_id: UUID,
    limit: int = 50,
    before: Optional[datetime] = None,
) -> list[Message]:
    stmt = select(Message).where(Message.session_id == session_id)
    if before is not None:
        stmt = stmt.where(Message.created_at < before)
    stmt = stmt.order_by(desc(Message.created_at), desc(Message.id)).limit(limit)
    return list(db.scalars(stmt))

# Updates
def update_session_title(db: Session, *, session_id: UUID, title: str) -> ChatSession | None:
    sess = db.get(ChatSession, session_id)
    if not sess:
        return None
    sess.title = title
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess
