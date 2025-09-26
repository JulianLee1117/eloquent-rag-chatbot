from __future__ import annotations
from typing import List, Optional, Set, Dict, Tuple
import logging
import re
from pinecone.grpc import PineconeGRPC as Pinecone
from ..core.config import settings
from .types import Doc
from .embedder import embed_query


_pc = Pinecone(api_key=settings.pinecone_api_key)
_index = _pc.Index(host=str(settings.pinecone_host))
logger = logging.getLogger("rag.retriever")

DEFAULT_TOP_K = 10

# Expanded synonyms per category for robust matching (login/log in/sign in, fees, etc.)
CATEGORY_SYNONYMS: Dict[str, List[str]] = {
    "Account & Registration": [
        "create account", "register", "sign up", "open account", "eligible",
        "verify identity", "kyc",
    ],
    "Payments & Transactions": [
        "payment", "payments", "transfer", "transaction", "transactions", "ach",
        "fees", "fee", "charges", "charge", "atm", "reverse", "cancel",
    ],
    "Security & Fraud Prevention": [
        "2fa", "two factor", "security", "fraud", "suspicious", "unauthorized",
        "lock account", "lock", "freeze",
    ],
    "Regulations & Compliance": [
        "regulated", "license", "licence", "kyc", "aml", "compliance",
        "insured", "fdic",
    ],
    "Technical Support & Troubleshooting": [
        "login", "log in", "sign in", "signin", "unable to log in", "cannot login",
        "can't log in", "cant log in", "forgot password", "reset password",
        "locked out", "error", "app crash", "troubleshoot",
    ],
}


def _normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _decompose_query(q: str) -> List[str]:
    """Split multi-intent queries into short clauses.

    Heuristic splitter on conjunctions/punctuation. Keeps clauses that have at least
    a few tokens to avoid noise.
    """
    qn = " " + _normalize(q) + " "
    parts = re.split(r"\b(?:and|also|but|;|\?|\.|!|,)\b", qn)
    clauses = [p.strip() for p in parts if len(p.strip()) > 0]
    out: List[str] = []
    for c in clauses:
        if len(c.split()) >= 3:
            out.append(c)
    clauses_out = out or [qn.strip()]
    logger.debug("retriever.decompose: query=%s clauses=%s", q[:120], clauses_out)
    return clauses_out


def _guess_categories_synonyms(q: str) -> Set[str]:
    qn = _normalize(q)
    cats: Set[str] = set()
    for cat, syns in CATEGORY_SYNONYMS.items():
        for s in syns:
            if s in qn:
                cats.add(cat)
                break
    return cats


 



def _pinecone_query(vector: List[float], top_k: int, filt: Optional[dict]) -> List[Doc]:
    res = _index.query(
        vector=vector,
        top_k=top_k,
        include_metadata=True,
        filter=filt,
        namespace="",
    )
    docs: List[Doc] = []
    for match in getattr(res, "matches", []) or []:
        md = getattr(match, "metadata", {}) or {}
        text = md.get("text") or md.get("chunk_text") or ""
        docs.append(Doc(
            id=str(match.id),
            text=text,
            score=float(match.score or 0.0),
            category=md.get("category"),
        ))
    logger.debug(
        "retriever.query: filt=%s returned=%d top_id_scores=%s",
        filt,
        len(docs),
        [(d.id, round(d.score, 4)) for d in docs[:3]],
    )
    return docs


def retrieve_optimal(query_text: str, final_k: int = 4) -> List[Doc]:
    """Multi-intent retrieval with soft category filtering and diversification.

    Steps per clause:
      - Guess categories using expanded synonyms.
      - If exactly one category: run filtered dense query; otherwise unfiltered.
      - If filtered results are empty, retry unfiltered.
    Union results across clauses, prefer one per clause first, then fill by score.
    """
    clauses = _decompose_query(query_text)
    bucketed: List[Tuple[int, Doc]] = []

    for idx, clause in enumerate(clauses):
        emb = embed_query(clause)
        cats_syn = _guess_categories_synonyms(clause)
        cats = set(cats_syn)

        filt: Optional[dict] = None
        if len(cats) == 1:
            only = next(iter(cats))
            filt = {"category": {"$eq": only}}
        logger.debug("retriever.clause: i=%d text=%s cats=%s filt=%s", idx, clause[:120], list(cats), filt)

        docs = _pinecone_query(emb, top_k=DEFAULT_TOP_K, filt=filt)
        if not docs:
            # fallback to unfiltered if filter was too strict
            docs = _pinecone_query(emb, top_k=DEFAULT_TOP_K, filt=None)

        # keep a small set per clause to allow diversification downstream
        for d in docs[: min(5, len(docs))]:
            bucketed.append((idx, d))

    if not bucketed:
        return []

    # Deduplicate while keeping highest score per id
    by_id: Dict[str, Tuple[int, Doc]] = {}
    for idx, d in bucketed:
        existing = by_id.get(d.id)
        if not existing or d.score > existing[1].score:
            by_id[d.id] = (idx, d)

    # Fair-share: one best per clause
    selected: List[Doc] = []
    seen_ids: Set[str] = set()
    for i in range(len(clauses)):
        best_for_clause: Optional[Doc] = None
        for idx, d in sorted(by_id.values(), key=lambda x: x[1].score, reverse=True):
            if idx == i and d.id not in seen_ids:
                best_for_clause = d
                break
        if best_for_clause is not None:
            selected.append(best_for_clause)
            seen_ids.add(best_for_clause.id)

    # Fill remaining slots by global score
    if len(selected) < final_k:
        pool = [d for _, d in sorted(by_id.values(), key=lambda x: x[1].score, reverse=True)]
        for d in pool:
            if d.id in seen_ids:
                continue
            selected.append(d)
            seen_ids.add(d.id)
            if len(selected) >= final_k:
                break

    logger.debug(
        "retriever.selected: query_preview=%s selected=%s",
        query_text[:120],
        [(d.id, round(d.score, 4), d.category) for d in selected],
    )
    return selected[:final_k]

