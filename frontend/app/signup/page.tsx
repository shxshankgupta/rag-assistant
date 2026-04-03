'use client';

import { FormEvent, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { loginUser, signupUser } from '@/lib/auth';

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      await signupUser({ email, username, password });
      await loginUser({ username, password });
      router.replace('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Signup failed.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
        <h1 className="text-2xl font-semibold mb-2">Create account</h1>
        <p className="text-sm text-slate-400 mb-6">Sign up and start chatting with your docs.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm mb-2">Email</label>
            <input
              type="email"
              className="w-full rounded-xl bg-slate-950 border border-slate-800 px-4 py-3 outline-none"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter email"
              required
            />
          </div>

          <div>
            <label className="block text-sm mb-2">Username</label>
            <input
              className="w-full rounded-xl bg-slate-950 border border-slate-800 px-4 py-3 outline-none"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Choose username"
              required
            />
          </div>

          <div>
            <label className="block text-sm mb-2">Password</label>
            <input
              type="password"
              className="w-full rounded-xl bg-slate-950 border border-slate-800 px-4 py-3 outline-none"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Choose password"
              required
            />
          </div>

          {error ? (
            <div className="rounded-xl border border-red-900 bg-red-950/40 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-60 px-4 py-3 font-medium"
          >
            {submitting ? 'Creating account...' : 'Sign up'}
          </button>
        </form>

        <p className="mt-6 text-sm text-slate-400">
          Already have an account?{' '}
          <Link href="/login" className="text-blue-400 hover:text-blue-300">
            Login
          </Link>
        </p>
      </div>
    </div>
  );
}