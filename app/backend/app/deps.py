"""Dependency helpers shared across routers.

Defines the `Identity` TypedDict and `get_current_identity` extractor which
prefers a valid `id_token` (JWT) cookie and falls back to an `anon_id` cookie.
"""
from typing import TypedDict
from fastapi import Request
from .core.security import decode_access_token

class Identity(TypedDict, total=False):
    user_id: str
    anon_id: str

def get_current_identity(request: Request) -> Identity:
    token = request.cookies.get("id_token")
    if token:
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            return {"user_id": payload["sub"]}
    anon_id = request.cookies.get("anon_id")
    if anon_id:
        return {"anon_id": anon_id}
    return {}
