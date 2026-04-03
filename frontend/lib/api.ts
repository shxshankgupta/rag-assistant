import { API_BASE_URL, API_TOKEN } from '@/lib/constants';

function normalizeApiBaseUrl(raw: string): string {
  const trimmed = raw.replace(/\/+$/, '');
  if (trimmed.endsWith('/api/v1')) {
    return trimmed;
  }
  return `${trimmed}/api/v1`;
}

export function getApiBaseUrl(): string {
  if (!API_BASE_URL) {
    throw new Error('API URL not configured. Set NEXT_PUBLIC_API_URL.');
  }
  return normalizeApiBaseUrl(API_BASE_URL);
}

/* ---------------- TOKEN HELPERS ---------------- */

function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('refresh_token');
}

export function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const envToken = API_TOKEN?.trim();
  const localToken = getAccessToken();
  const token = localToken || envToken;

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

/* ---------------- REFRESH TOKEN ---------------- */

export async function refreshAccessToken(): Promise<string> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) throw new Error('No refresh token');

  const response = await fetch(`${getApiBaseUrl()}/auth/refresh`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      refresh_token: refreshToken,
    }),
  });

  if (!response.ok) {
    throw new Error('Refresh token failed');
  }

  const data = await response.json();

  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);

  return data.access_token;
}

/* ---------------- MAIN FETCH WRAPPER ---------------- */

export async function apiFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  let token = getAccessToken();
  const isFormData = options.body instanceof FormData;

  const makeRequest = async (token: string | null) => {
    return fetch(`${getApiBaseUrl()}${url}`, {
      ...options,
      headers: {
        ...(options.headers || {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      },
    });
  };

  let response = await makeRequest(token);

  if (response.status === 401) {
    try {
      const newToken = await refreshAccessToken();
      response = await makeRequest(newToken);
    } catch (err) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.reload();
      throw err;
    }
  }

  return response;
}

/* ---------------- DOCUMENT API ---------------- */

export interface BackendDocument {
  id: string;
  status: string;
  processing_view?: string | null;
  celery_state?: string | null;
  error_message?: string | null;
}

export async function fetchDocument(documentId: string): Promise<BackendDocument> {
  const response = await apiFetch(`/documents/${documentId}`, {
    method: 'GET',
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Document ${documentId}: HTTP ${response.status} ${text}`);
  }

  return response.json();
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export type PollDocumentsResult =
  | { ok: true }
  | { ok: false; reason: 'failed'; message: string }
  | { ok: false; reason: 'timeout'; message: string };

export async function pollDocumentsUntilReady(
  documentIds: string[],
  options?: {
    intervalMs?: number;
    timeoutMs?: number;
    onStatus?: (id: string, doc: BackendDocument) => void;
  }
): Promise<PollDocumentsResult> {
  if (documentIds.length === 0) {
    return { ok: true };
  }

  const intervalMs = options?.intervalMs ?? 8000;
  const timeoutMs = options?.timeoutMs ?? 5 * 60 * 1000;
  const deadline = Date.now() + timeoutMs;
  const pending = new Set(documentIds);

  while (pending.size > 0) {
    if (Date.now() > deadline) {
      return {
        ok: false,
        reason: 'timeout',
        message: 'Document processing is taking longer than expected.',
      };
    }

    for (const id of [...pending]) {
      try {
        const doc = await fetchDocument(id);
        options?.onStatus?.(id, doc);

        if (doc.status === 'failed' || doc.processing_view === 'failed') {
          return {
            ok: false,
            reason: 'failed',
            message: doc.error_message || 'Document processing failed.',
          };
        }

        if (doc.status === 'ready' || doc.processing_view === 'completed') {
          pending.delete(id);
        }
      } catch {
        // ignore
      }
    }

    if (pending.size > 0) {
      await sleep(intervalMs);
    }
  }

  return { ok: true };
}