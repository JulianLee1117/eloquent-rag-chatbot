import './globals.css';
import { ReactNode } from 'react';
import ClientProviders from '@/components/ClientProviders';

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0 }}>
        <ClientProviders>{children}</ClientProviders>
      </body>
    </html>
  );
}
