const API = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export async function ensureAnonCookie(): Promise<void> {
  // Hitting a Next.js route that sets anon cookie is best-practice,
  // but for simplicity we set a client cookie if missing.
  // Anon id is not sensitive; JWT remains HttpOnly on the backend.
  if (document.cookie.includes('anon_id=')) return;
  const id = crypto.randomUUID();
  // persistent cookie (~365 days)
  document.cookie = `anon_id=${id}; Path=/; Max-Age=${3600 * 24 * 365}; SameSite=Strict`;
}

export type Session = {
  id: string; user_id?: string | null; anon_id?: string | null;
  title?: string | null; created_at: string;
};

export type Message = {
  id: string; session_id: string; role: 'user'|'assistant'|'system';
  content: string; tokens_in: number; tokens_out: number; created_at: string;
};

export type Citation = {
  id: string;
  rank: number;
  category?: string | null;
};

export async function listSessions(): Promise<Session[]> {
  const r = await fetch(`${API}/sessions`, { credentials: 'include' });
  if (!r.ok) throw new Error('failed to list sessions');
  return r.json();
}

export async function createSession(title?: string): Promise<Session> {
  const r = await fetch(`${API}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ title }),
  });
  if (!r.ok) throw new Error('failed to create session');
  return r.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const r = await fetch(`${API}/sessions/${sessionId}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (!r.ok) throw new Error('failed to delete session');
}

export async function updateSessionTitle(sessionId: string, title: string): Promise<Session> {
  const r = await fetch(`${API}/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ title }),
  });
  if (!r.ok) throw new Error('failed to update session');
  return r.json();
}

// --- Auth ---
export async function register(email: string, password: string): Promise<void> {
  const r = await fetch(`${API}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) throw new Error('failed to register');
}

export async function login(email: string, password: string): Promise<void> {
  const r = await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) throw new Error('failed to login');
}

export async function logout(): Promise<void> {
  const r = await fetch(`${API}/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!r.ok) throw new Error('failed to logout');
}

export async function whoami(): Promise<{ user_id?: string; anon_id?: string | null }> {
  const r = await fetch(`${API}/auth/whoami`, { credentials: 'include' });
  if (!r.ok) throw new Error('failed to get identity');
  return r.json();
}

export async function getMessages(sessionId: string, limit = 50, before?: string): Promise<Message[]> {
  const url = new URL(`${API}/sessions/${sessionId}/messages`);
  url.searchParams.set('limit', String(limit));
  if (before) url.searchParams.set('before', before);
  const r = await fetch(url, { credentials: 'include' });
  if (!r.ok) throw new Error('failed to fetch messages');
  return r.json();
}

export type DonePayload = {
    citations: Citation[];
    usage: { tokens_in: number; tokens_out: number };
    session_id: string;
};

export async function* streamChat(sessionId: string, message: string): AsyncGenerator<
  { event: 'token'; data: { token: string } } |
  { event: 'done'; data: DonePayload } |
  { event: 'error'; data: { message: string } }
> {
  const r = await fetch(`${API}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
    credentials: 'include',
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!r.ok || !r.body) throw new Error('stream failed to start');

  const reader = r.body.getReader(); // ReadableStream reader
  const decoder = new TextDecoder();
  let buf = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line (double newline)
    // Each block contains lines like: "event: token" and "data: {...}"
    let idx: number;
    while ((idx = buf.indexOf('\n\n')) !== -1) {
      const raw = buf.slice(0, idx).trim();
      buf = buf.slice(idx + 2);
      // Parse block
      let event = 'message';
      const dataLines: string[] = [];
      for (const line of raw.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
      }
      const dataStr = dataLines.join('\n');
      let data: unknown = dataStr;
      try { data = JSON.parse(dataStr); } catch {}

      if (event === 'token') {
        yield { event, data: data as { token: string } };
      } else if (event === 'done') {
        yield { event, data: data as DonePayload };
      } else if (event === 'error') {
        yield { event, data: data as { message: string } };
      }
    }
  }
}
