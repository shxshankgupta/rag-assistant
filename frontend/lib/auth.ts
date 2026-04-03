'use client';

import { apiFetch, getApiBaseUrl } from '@/lib/api';

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export interface SignupPayload {
  email: string;
  username: string;
  password: string;
}

export interface SignupResponse {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
}

export function storeTokens(tokens: AuthTokens) {
  if (typeof window === 'undefined') return;
  localStorage.setItem('access_token', tokens.access_token);
  localStorage.setItem('refresh_token', tokens.refresh_token);
}

export function clearTokens() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

export function getStoredAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

export function getStoredRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('refresh_token');
}

export function isAuthenticated(): boolean {
  return !!getStoredAccessToken();
}

export async function loginUser(payload: LoginPayload): Promise<AuthTokens> {
  const response = await fetch(`${getApiBaseUrl()}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  const text = await response.text();
  let data: AuthTokens | { detail?: string };

  try {
    data = JSON.parse(text);
  } catch {
    throw new Error('Invalid server response during login.');
  }

  if (!response.ok) {
    throw new Error((data as { detail?: string }).detail || 'Login failed.');
  }

  const tokens = data as AuthTokens;
  storeTokens(tokens);
  return tokens;
}

export async function signupUser(payload: SignupPayload): Promise<SignupResponse> {
  const response = await fetch(`${getApiBaseUrl()}/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  const text = await response.text();
  let data: SignupResponse | { detail?: string };

  try {
    data = JSON.parse(text);
  } catch {
    throw new Error('Invalid server response during signup.');
  }

  if (!response.ok) {
    throw new Error((data as { detail?: string }).detail || 'Signup failed.');
  }

  return data as SignupResponse;
}

export async function fetchCurrentUser() {
  const response = await apiFetch('/auth/me', {
    method: 'GET',
  });

  const text = await response.text();
  let data: unknown = null;

  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    throw new Error('Invalid server response while fetching current user.');
  }

  if (!response.ok) {
    const message =
      typeof data === 'object' && data !== null && 'detail' in data
        ? String((data as { detail?: unknown }).detail || 'Failed to fetch user.')
        : 'Failed to fetch user.';
    throw new Error(message);
  }

  return data;
}