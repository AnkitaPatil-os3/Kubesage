'use client';

import { SessionProvider } from 'next-auth/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import { SSRProvider } from 'react-bootstrap';
import useStore from '../lib/store';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  const { darkMode } = useStore();
  
  // Handle dark mode class on document
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      document.body.setAttribute('data-bs-theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      document.body.setAttribute('data-bs-theme', 'light');
    }
  }, [darkMode]);
  
  return (
    <SessionProvider>
      <QueryClientProvider client={queryClient}>
        <SSRProvider>
          {children}
        </SSRProvider>
      </QueryClientProvider>
    </SessionProvider>
  );
}
