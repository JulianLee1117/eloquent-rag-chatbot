from __future__ import annotations
import httpx
from openai import OpenAI, DefaultHttpxClient
from ..core.config import settings

_client: OpenAI | None = None

def get_openai() -> OpenAI:
    global _client
    if _client:
        return _client
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY not configured")
    _client = OpenAI(
        api_key=settings.llm_api_key,
        http_client=DefaultHttpxClient(
            timeout=httpx.Timeout(60.0, read=30.0, write=10.0, connect=5.0)
        ),
    )
    return _client
