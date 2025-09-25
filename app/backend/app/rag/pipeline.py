from collections.abc import Iterator
from typing import Iterable

class StreamResult:
    """
    Yields tokens AND gathers final artifacts for persistence.
    """
    def __init__(self, tokens: Iterable[str]):
        self._tokens = iter(tokens)
        self.buffer = []  # collected tokens for assistant content
        self.citations: list[dict] = []  # fill with RAG later
        self.usage = {"tokens_in": 0, "tokens_out": 0}

    def __iter__(self) -> Iterator[str]:
        for tok in self._tokens:
            self.buffer.append(tok)
            yield tok
        # finalize usage
        self.usage["tokens_out"] = sum(len(t.split()) for t in self.buffer)

def fake_tokenize(text: str) -> list[str]:
    """
    Naive tokenizer for demo streaming.
    """
    words = text.split()
    return [w + " " for w in words]  # keep spaces so curl shows flowing text

def generate_stream(user_prompt: str) -> StreamResult:
    # Simple echo → pretend model that replies with "You said: <prompt>"
    preface = "You said: "
    toks = [preface] + fake_tokenize(user_prompt)
    result = StreamResult(toks)
    result.usage["tokens_in"] = len(user_prompt.split())
    return result
