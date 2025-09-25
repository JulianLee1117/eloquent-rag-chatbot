'use client';

import { ReactNode, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

export default function ClientProviders({ children }: { children: ReactNode }) {
  // Create once on the client
  const [qc] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={qc}>
      {children}
      {/* Devtools optional; remove in production */}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
