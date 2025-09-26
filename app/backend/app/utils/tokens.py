from __future__ import annotations
import logging
from ..core.config import settings

logger = logging.getLogger("utils.tokens")


def _get_model_name() -> str:
    # Prefer the configured model; otherwise fallback to a common tokenizer
    # that works well for GPT-4/3.5 style models.
    return settings.llm_model or "gpt-4o-mini"


def count_tokens(text: str) -> int:
    """Count tokens for the configured model using tiktoken.

    Falls back to a rough whitespace split if tiktoken is unavailable.
    """
    try:
        import tiktoken  # type: ignore

        model = _get_model_name()
        try:
            enc = tiktoken.encoding_for_model(model)
        except Exception:
            # Fallback to a broadly compatible tokenizer
            logger.debug("tokens: encoding_for_model failed for %s; using cl100k_base", model)
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text or ""))
    except Exception:
        # Very rough fallback when tiktoken is unavailable
        logger.debug("tokens: tiktoken unavailable; falling back to whitespace split")
        return len((text or "").split())


