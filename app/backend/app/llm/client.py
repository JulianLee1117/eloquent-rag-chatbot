from __future__ import annotations
"""OpenAI client factory with tuned HTTP timeouts for streaming.

This module exposes a singleton OpenAI client configured with slightly
longer read timeouts to better accommodate server-sent events (SSE)
token streams without premature read timeouts.
"""

import httpx
from openai import OpenAI, DefaultHttpxClient
from ..core.config import settings

_client: OpenAI | None = None

def get_openai() -> OpenAI:
    """Return a process-wide OpenAI client instance.

    The client uses conservative HTTP timeouts suitable for streamed
    responses. If your deployment observes long token gaps, consider
    increasing the read timeout further.
    """
    global _client
    if _client:
        return _client
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY not configured")
    _client = OpenAI(
        api_key=settings.llm_api_key,
        http_client=DefaultHttpxClient(
            # connect/read/write in seconds
            timeout=httpx.Timeout(60.0, read=180.0, write=10.0, connect=5.0)
        ),
    )
    return _client
