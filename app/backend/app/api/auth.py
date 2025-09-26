"""Authentication API.

Provides simple email/password registration and login using JWT (HS256)
stored in an HttpOnly cookie. Also exposes `whoami` to surface the current
identity (user or anon) and `logout` to clear credentials.

In production, ensure `JWT_SECRET` is strong, cookies are `Secure`, and
`CORS_ORIGINS` is restricted to trusted origins.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from pydantic import BaseModel
from ..core.config import settings
from ..core.security import verify_password, create_access_token, decode_access_token, hash_password
from ..db.base import get_db
from ..db import crud

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "id_token"
ANON_COOKIE = "anon_id"

def _cookie_kwargs():
    """Return consistent cookie flags for auth cookies.

    - HttpOnly prevents access from JS.
    - SameSite defaults to Strict; adjust to "None" if serving API cross-site.
    - In dev over http, `secure=False` is required for the cookie to set.
    """
    secure = False if settings.python_env == "dev" else True
    return dict(httponly=True, secure=secure, samesite="strict", path="/")

class LoginIn(BaseModel):
    email: str
    password: str

class RegisterIn(BaseModel):
    email: str
    password: str

@router.post("/register")
def register(body: RegisterIn, response: Response, db = Depends(get_db)):
    """Create a new user and set an auth cookie.

    Returns {"ok": True} on success and sets `id_token` (JWT) on the response.
    """
    existing = crud.get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = crud.create_user(db, email=body.email, hashed_password=hash_password(body.password))
    token = create_access_token({"sub": str(user.id)})
    response.set_cookie(COOKIE_NAME, token, **_cookie_kwargs())
    return {"ok": True}

@router.post("/login")
def login(body: LoginIn, response: Response, db = Depends(get_db)):
    """Authenticate a user by email/password and set the auth cookie.

    Returns {"ok": True} on success.
    """
    user = crud.get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id)})
    response.set_cookie(COOKIE_NAME, token, **_cookie_kwargs())
    return {"ok": True}

@router.post("/logout")
def logout(response: Response):
    """Clear the auth cookie to log the user out."""
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}

@router.get("/whoami")
def whoami(request: Request):
    """Return the current identity: user_id if logged in; else anon_id if present."""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            return {"user_id": payload["sub"]}
    anon_id = request.cookies.get(ANON_COOKIE)
    return {"anon_id": anon_id} if anon_id else {"anon_id": None}
