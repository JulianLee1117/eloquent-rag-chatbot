from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Doc:
    id: str
    text: str
    score: float
    category: str | None = None

    def to_citation(self, rank: int) -> dict:
        return {"id": self.id, "rank": rank, "category": self.category}


