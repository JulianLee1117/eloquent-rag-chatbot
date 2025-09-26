'use client';

import { useEffect, useMemo, useRef } from 'react';
import { Message } from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function MessageList({
  messages,
  isStreaming,
  pendingText,
}: {
  messages: Message[];
  isStreaming: boolean;
  pendingText: string;
}) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, pendingText]);

  const ordered = useMemo(() => {
    return [...messages].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
  }, [messages]);

  return (
    <div className="messages">
      {ordered.map((m) => (
        <div key={m.id} className={`message-row ${m.role === 'user' ? 'user' : 'assistant'}`}>
          <div>
            <div className="sender">{m.role === 'user' ? 'You' : 'Assistant'}</div>
            <div className={`bubble ${m.role === 'user' ? 'user' : 'assistant'}`}>
              {m.role === 'assistant' ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {m.content}
                </ReactMarkdown>
              ) : (
                m.content
              )}
            </div>
          </div>
        </div>
      ))}
      {isStreaming && pendingText && (
        <div className="message-row assistant">
          <div>
            <div className="sender">Assistant</div>
            <div className="bubble assistant">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {pendingText}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
