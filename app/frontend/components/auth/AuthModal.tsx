'use client';

import { useEffect, useState } from 'react';
import { login, logout, register, whoami } from '@/lib/api';
import { useQueryClient } from '@tanstack/react-query';

export default function AuthModal({ open, onClose, onAuthChanged }: { open: boolean; onClose: () => void; onAuthChanged?: () => void; }) {
  const qc = useQueryClient();
  const [mode, setMode] = useState<'login'|'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [me, setMe] = useState<{ user_id?: string; anon_id?: string | null }>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { if (open) { whoami().then(setMe).catch(() => {}); setError(null); } }, [open]);

  if (!open) return null;

  async function handleAuth() {
    try {
      setError(null);
      if (mode === 'login') await login(email, password);
      else await register(email, password);
      setEmail(''); setPassword('');
      await qc.invalidateQueries({ queryKey: ['sessions'] });
      setMe(await whoami());
      onAuthChanged?.();
      onClose();
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Authentication failed';
      setError(msg);
    }
  }

  async function handleLogout() {
    await logout();
    await qc.invalidateQueries({ queryKey: ['sessions'] });
    onAuthChanged?.();
    onClose();
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
      <div style={{ width: 'min(92vw, 420px)', border: '1px solid var(--border)', background: 'var(--panel-2)', color: 'var(--foreground)', borderRadius: 12, boxShadow: '0 10px 30px rgba(0,0,0,.15)' }}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <b>{me.user_id ? 'Account' : mode === 'login' ? 'Sign in' : 'Create account'}</b>
          <button className="btn" onClick={onClose}>Close</button>
        </div>
        <div style={{ padding: 16, display: 'grid', gap: 10 }}>
          {me.user_id ? (
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button className="btn" onClick={handleLogout}>Sign out</button>
            </div>
          ) : (
            <>
              <input type="email" placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)}
                style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid var(--border)', background: 'var(--panel)', color: 'var(--foreground)' }} />
              <input type="password" placeholder="password" value={password} onChange={(e) => setPassword(e.target.value)}
                style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid var(--border)', background: 'var(--panel)', color: 'var(--foreground)' }} />
              {error && <div style={{ color: 'tomato', fontSize: 12 }}>{error}</div>}
              <div style={{ display: 'flex', gap: 8, justifyContent: 'space-between' }}>
                <button className="btn btn-primary" onClick={handleAuth} style={{ flex: 1 }}>{mode === 'login' ? 'Sign in' : 'Create account'}</button>
                <button className="btn" onClick={() => setMode(mode === 'login' ? 'register' : 'login')} style={{ width: 150 }}>{mode === 'login' ? 'Register' : 'Have an account?'}</button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}


