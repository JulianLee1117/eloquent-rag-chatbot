import types
from uuid import UUID


def test_chat_stream_monkeypatched(client, monkeypatch):
    # Prepare identity as anon
    client.cookies.set("anon_id", "pytest_sse")

    # Create a session
    r = client.post("/sessions", json={"title": "SSE chat"})
    assert r.status_code == 201
    session_id = r.json()["id"]
    UUID(session_id)

    # Monkeypatch ChatService.stream_for_session to avoid external calls
    from app.services.chat_service import ChatService, StreamResult

    def fake_stream_for_session(db, sid):  # sid is UUID
        def _iter():
            yield "Hello, "
            yield "world!"
        # Minimal usage and no citations
        sr = StreamResult(_iter(), citations=[], tokens_in=5)
        return sr

    monkeypatch.setattr(ChatService, "stream_for_session", staticmethod(fake_stream_for_session))

    # Hit /chat and collect SSE frames
    r = client.post("/chat", json={"session_id": session_id, "message": "Hi"}, headers={"Accept": "text/event-stream"})
    assert r.status_code == 200
    body = r.text
    # Expect open, token, token, done events
    assert "event: open" in body
    assert "event: token" in body
    assert "Hello, " in body or "Hello," in body
    assert "world!" in body
    assert "event: done" in body

