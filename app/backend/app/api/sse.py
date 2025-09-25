import json

def sse_event(event: str, data: dict | str) -> bytes:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    # Each SSE message block ends with a blank line
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")
