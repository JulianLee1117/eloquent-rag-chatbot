import uuid
from sqlalchemy import select
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
