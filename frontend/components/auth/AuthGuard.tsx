'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { isAuthenticated } from '@/lib/auth';

interface AuthGuardProps {
  children: React.ReactNode;
}

export default function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const publicPaths = ['/login', '/signup'];
    const loggedIn = isAuthenticated();

    if (!loggedIn && !publicPaths.includes(pathname)) {
      router.replace('/login');
      return;
    }

    if (loggedIn && publicPaths.includes(pathname)) {
      router.replace('/');
      return;
    }

    setChecked(true);
  }, [pathname, router]);

  if (!checked) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-200 flex items-center justify-center">
        <div className="text-sm text-slate-400">Loading...</div>
      </div>
    );
  }

  return <>{children}</>;
}