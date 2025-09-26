'use client';

import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ensureAnonCookie, listSessions, createSession, deleteSession, updateSessionTitle, getMessages, streamChat, type Message, type Session } from '@/lib/api';
import SessionSidebar from '@/components/SessionSidebar';
import MessageList from '@/components/MessageList';
import Composer from '@/components/Composer';

export default function ChatPage() {
  const qc = useQueryClient();
  const [current, setCurrent] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [pendingText, setPendingText] = useState<string>(''); // live tokens
  // citations removed per product decision

  // ensure anon cookie on first load (non-sensitive; JWT stays HttpOnly server-side)
  useEffect(() => { ensureAnonCookie(); }, []);

  const sessionsQ = useQuery({
    queryKey: ['sessions'],
    queryFn: listSessions,
    refetchOnWindowFocus: false,
  });

  // First session bootstrap
  useEffect(() => {
    if (sessionsQ.data && sessionsQ.data.length > 0 && !current) {
      setCurrent(sessionsQ.data[0].id);
    }
  }, [sessionsQ.data, current]);

  const createSessionMut = useMutation({
    mutationFn: (title?: string) => createSession(title),
    onSuccess: async (s) => {
      await qc.invalidateQueries({ queryKey: ['sessions'] });
      setCurrent(s.id);
    },
  });

  const messagesQ = useQuery({
    queryKey: ['messages', current],
    queryFn: () => current ? getMessages(current) : Promise.resolve([] as Message[]),
    enabled: !!current,
    refetchOnWindowFocus: false,
  });

  // Reset transient UI state when switching sessions
  useEffect(() => { setPendingText(''); }, [current]);

  async function handleSend(text: string) {
    let sid = current;
    if (!sid) {
      const created = await createSessionMut.mutateAsync('New chat');
      sid = created.id;
    }
    if (!sid) {
      const sessions = qc.getQueryData<Session[]>(['sessions']) ?? [];
      sid = sessions[0]?.id ?? null;
    }
    if (!sid) {
      console.error('No session available to send message');
      return;
    }
    setIsStreaming(true);
    setPendingText('');

    // optimistic insert user message; also set a title if session was Untitled
    qc.setQueryData<Message[]>(['messages', sid], (prev = []) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        session_id: sid,
        role: 'user',
        content: text,
        tokens_in: 0,
        tokens_out: 0,
        created_at: new Date().toISOString(),
      },
    ]);

    // If the session has no title yet, set it to the first user message (truncated)
    const sessions = qc.getQueryData<Session[]>(['sessions']) || [];
    const s = sessions.find(x => x.id === sid);
    if (s && (!s.title || s.title === 'Untitled')) {
      const newTitle = text.slice(0, 32).trim();
        // update title
      qc.setQueryData<Session[]>(['sessions'], sessions.map(x => x.id === sid ? { ...x, title: newTitle } : x));
      try { await updateSessionTitle(sid, newTitle); } catch (e) { console.warn('Failed to persist title', e); }
    }

    // stream assistant (no placeholder to avoid duplicate rendering)

    try {
      for await (const evt of streamChat(sid, text)) {
        if (evt.event === 'token') {
          setPendingText((t) => t + evt.data.token);
        } else if (evt.event === 'done') {
          // citations removed
        } else if (evt.event === 'error') {
          console.error('SSE error', evt.data);
        }
      }
      // Re-sync from DB at the end (ensures tokens/usage persisted)
      await qc.invalidateQueries({ queryKey: ['messages', sid] });
    } finally {
      setIsStreaming(false);
      setPendingText('');
    }
  }

  return (
    <div className="layout">
      <SessionSidebar
        sessions={sessionsQ.data || []}
        current={current}
        onNew={() => createSessionMut.mutate(undefined)}
        onSelect={setCurrent}
        onAuthChanged={async () => {
          setCurrent(null);
          qc.removeQueries({ queryKey: ['messages'] });
          await qc.invalidateQueries({ queryKey: ['sessions'] });
        }}
        onDelete={async (id) => {
          if (!confirm('Delete this chat? This cannot be undone.')) return;
          await deleteSession(id);
          await qc.invalidateQueries({ queryKey: ['sessions'] });
          // if deleting current, move to first available
          setCurrent((prev) => {
            if (prev !== id) return prev;
            const rows = qc.getQueryData<Session[]>(['sessions']) || [];
            const next = rows.find(s => s.id !== id)?.id || null;
            return next;
          });
        }}
      />
      <div className="chat-area">
        <div className="chat-header"><strong>Fintech Assistant</strong></div>
        <MessageList messages={messagesQ.data || []} isStreaming={isStreaming} pendingText={pendingText} />
        <Composer onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  );
}
