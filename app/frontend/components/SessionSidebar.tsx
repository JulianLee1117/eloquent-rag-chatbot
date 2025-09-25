'use client';

import { Session } from '@/lib/api';
import { useState } from 'react';
import AuthModal from '@/components/auth/AuthModal';

export default function SessionSidebar({
  sessions,
  current,
  onNew,
  onSelect,
  onDelete,
  onAuthChanged,
}: {
  sessions: Session[];
  current: string | null;
  onNew: () => void;
  onSelect: (id: string) => void;
  onDelete?: (id: string) => void;
  onAuthChanged?: () => void;
}) {
  const [authOpen, setAuthOpen] = useState(false);
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <b>Chats</b>
        <div style={{ display: 'flex', gap: 6 }}>
          <button className="btn" onClick={() => setAuthOpen(true)}>Account</button>
          <button className="btn btn-primary" onClick={onNew}>+ New</button>
        </div>
      </div>
      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} onAuthChanged={onAuthChanged} />
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {sessions.map(s => (
          <li key={s.id}>
            <div style={{ display: 'flex', gap: 6, alignItems: 'stretch' }}>
              <button
                onClick={() => onSelect(s.id)}
                className="btn"
                style={{ flex: 1, textAlign: 'left', marginBottom: 6, background: current === s.id ? 'var(--panel-2)' : 'var(--panel)' }}
              >
                {s.title || 'Untitled'}<br />
                <small style={{ color: 'var(--muted)' }}>{new Date(s.created_at).toLocaleString()}</small>
              </button>
              {onDelete && (
                <button
                  title="Delete chat"
                  onClick={() => onDelete(s.id)}
                  className="btn"
                  style={{ marginBottom: 6 }}
                >
                  ✕
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
