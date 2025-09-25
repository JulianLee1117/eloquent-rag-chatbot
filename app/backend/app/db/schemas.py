from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from .models import Role

class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # pydantic v2 replacement for orm_mode
# Pydantic v2 docs call this `from_attributes`; formerly `orm_mode`. :contentReference[oaicite:4]{index=4}

# --- User ---
class UserCreate(BaseModel):
    email: str
    password: str

class UserOut(ORMModel):
    id: UUID
    email: str
    created_at: datetime

# --- Session ---
class SessionCreate(BaseModel):
    title: Optional[str] = None
    anon_id: Optional[str] = None

class SessionOut(ORMModel):
    id: UUID
    user_id: Optional[UUID] = None
    anon_id: Optional[str] = None
    title: Optional[str] = None
    created_at: datetime

# --- Message ---
class MessageCreate(BaseModel):
    role: Role
    content: str
    tokens_in: int = 0
    tokens_out: int = 0

class MessageOut(ORMModel):
    id: UUID
    session_id: UUID
    role: Role
    content: str
    tokens_in: int
    tokens_out: int
    created_at: datetime
