from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from pydantic import BaseModel
from ..core.config import settings
from ..core.security import verify_password, create_access_token, decode_access_token
from ..db.base import get_db
from ..db import crud

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "id_token"
ANON_COOKIE = "anon_id"

def _cookie_kwargs():
    # Cookies: HttpOnly, SameSite=Strict. For local dev over http, set secure=False or cookie won't set.
    secure = False if settings.python_env == "dev" else True
    return dict(httponly=True, secure=secure, samesite="strict", path="/")

class LoginIn(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(body: LoginIn, response: Response, db = Depends(get_db)):
    user = crud.get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id)})
    response.set_cookie(COOKIE_NAME, token, **_cookie_kwargs())
    return {"ok": True}

@router.post("/logout")
def logout(response: Response):
    # Clear JWT cookie
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}

@router.get("/whoami")
def whoami(request: Request):
    # Prefer user JWT; else anon id
    token = request.cookies.get(COOKIE_NAME)
    if token:
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            return {"user_id": payload["sub"]}
    anon_id = request.cookies.get(ANON_COOKIE)
    return {"anon_id": anon_id} if anon_id else {"anon_id": None}
