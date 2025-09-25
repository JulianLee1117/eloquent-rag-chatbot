'use client';

import { useState } from 'react';

export default function Composer({ onSend, disabled }: { onSend: (text: string) => void | Promise<void>; disabled?: boolean; }) {
  const [text, setText] = useState('');

  async function submit() {
    const t = text.trim();
    if (!t || disabled) return;
    setText('');
    await onSend(t);
  }

  return (
    <div className="composer">
      <div className="input-wrap">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Ask about your account, payments, or security..."
          rows={1}
          className="textarea"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault(); submit();
            }
          }}
          disabled={disabled}
        />
        <div className="composer-actions">
          <button className="send-btn" onClick={submit} disabled={disabled || !text.trim()}>Send</button>
        </div>
      </div>
    </div>
  );
}
