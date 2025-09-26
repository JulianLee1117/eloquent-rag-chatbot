"""Prompt utilities for assembling system/user messages with citations."""
from __future__ import annotations

from typing import List
import re
from .types import Doc


SYSTEM_PROMPT = """You are the Fintech Assistant for a consumer fintech.
Follow these rules strictly:
- Use ONLY the provided context; do NOT invent facts.
- Cite sources inline using the format [FAQ x], for example [FAQ 11]. The FAQ number x is shown next to each context entry.
- If the answer is not in context, say you don’t know and suggest what to ask next.
- Keep answers concise, step-by-step if needed, and safe (never request sensitive data).

You will be given a section called "Context documents". Only answer using these.
"""


def _extract_faq_num(doc_id: str) -> str:
    m = re.search(r"(\d+)", doc_id or "")
    return m.group(1) if m else (doc_id or "n/a")


def format_context(docs: List[Doc]) -> str:
    lines = []
    for i, d in enumerate(docs, start=1):
        faq_num = _extract_faq_num(d.id)
        head = f"[FAQ {faq_num}] [{i}] (category: {d.category or 'n/a'}, id: {d.id})"
        lines.append(f"{head}\n{d.text}")
    return "\n\n".join(lines)


def build_messages(history: list[dict], user_question: str, docs: List[Doc]) -> list[dict]:
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    ctx = format_context(docs)
    messages.append({
        "role": "user",
        "content": f"Context documents:\n{ctx}",
    })
    for m in history:
        if m.get("role") in ("user", "assistant"):
            messages.append(m)
    messages.append({"role": "user", "content": user_question})
    return messages


