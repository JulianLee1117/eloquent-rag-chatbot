from uuid import UUID


def test_sessions_anon_flow(client):
    # Ensure anon_id cookie is set (simulate frontend behavior)
    client.cookies.set("anon_id", "pytest_anon")

    # Create session
    r = client.post("/sessions", json={"title": "Test chat"})
    assert r.status_code == 201
    s = r.json()
    assert UUID(s["id"])  # valid UUID
    session_id = s["id"]

    # List sessions (should include the new one)
    r = client.get("/sessions")
    assert r.status_code == 200
    rows = r.json()
    assert any(row["id"] == session_id for row in rows)

    # List messages (empty)
    r = client.get(f"/sessions/{session_id}/messages")
    assert r.status_code == 200
    assert r.json() == []

    # Update session title
    r = client.patch(f"/sessions/{session_id}", json={"title": "Renamed"})
    assert r.status_code == 200
    assert r.json()["title"] == "Renamed"

    # Delete session (soft delete)
    r = client.delete(f"/sessions/{session_id}")
    assert r.status_code == 204

    # After delete: listing messages returns empty
    r = client.get(f"/sessions/{session_id}/messages")
    assert r.status_code == 200
    assert r.json() == []


def test_auth_and_user_sessions_flow(client):
    # Register
    r = client.post("/auth/register", json={"email": "u@example.com", "password": "pw123456"})
    assert r.status_code == 200

    # whoami returns user_id
    r = client.get("/auth/whoami")
    assert r.status_code == 200
    assert "user_id" in r.json()

    # Create a user-owned session
    r = client.post("/sessions", json={"title": "User chat"})
    assert r.status_code == 201
    session_id = r.json()["id"]

    # List sessions includes it
    r = client.get("/sessions")
    assert r.status_code == 200
    assert any(s["id"] == session_id for s in r.json())

    # Logout and verify identity flips to anon (or None)
    r = client.post("/auth/logout")
    assert r.status_code == 200
    r = client.get("/auth/whoami")
    assert r.status_code == 200
    body = r.json()
    assert "user_id" not in body

