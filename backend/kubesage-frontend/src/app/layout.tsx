import { Inter } from 'next/font/google';
import { Metadata } from 'next';
import Navbar from '../components/layout/Navbar';
import './globals.scss';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'KubeSage - Kubernetes Management Platform',
  description: 'Manage your Kubernetes clusters with ease',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <Navbar />
          <main className="container py-4">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}
