from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from ..deps import get_current_identity, Identity
from ..db.base import get_db
from ..db import crud
from ..db.schemas import SessionOut

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.get("", response_model=list[SessionOut])
def list_my_sessions(identity: Identity = Depends(get_current_identity), db = Depends(get_db)):
    if not identity:
        # no JWT and no anon cookie -> nothing to show
        return []
    # For demo, fetch the most-recent session for anon OR all user sessions (you can refine later)
    if "user_id" in identity:
        # TODO: replace with a proper query filtering by user_id when you add CRUD
        # For now, return empty list to prove auth flow works
        return []
    if "anon_id" in identity:
        sess = crud.get_or_create_anon_session(db, anon_id=identity["anon_id"])
        return [SessionOut.model_validate(sess)]
    return []
