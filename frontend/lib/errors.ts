/**
 * Classify API failures for UX (copy, colors, retry policy).
 */

export type ApiErrorKind = 'network' | 'auth' | 'client' | 'server' | 'stream' | 'unknown';

export interface ClassifiedError {
  kind: ApiErrorKind;
  message: string;
  status?: number;
  /** Whether showing a "Retry" action makes sense */
  retryable: boolean;
}

function isClassifiedError(err: unknown): err is ClassifiedError {
  return (
    typeof err === 'object' &&
    err !== null &&
    'kind' in err &&
    'message' in err &&
    'retryable' in err
  );
}

function trimMessage(s: string, max = 400): string {
  const t = s.trim();
  return t.length > max ? `${t.slice(0, max)}…` : t;
}

export function parseFastApiDetail(bodyText: string): string {
  const raw = trimMessage(bodyText, 2000);
  try {
    const j = JSON.parse(bodyText) as { detail?: unknown };
    if (j?.detail == null) return raw;
    if (typeof j.detail === 'string') return trimMessage(j.detail);
    if (Array.isArray(j.detail)) {
      return trimMessage(
        j.detail
          .map((x) => (typeof x === 'object' && x && 'msg' in x ? String((x as { msg: string }).msg) : String(x)))
          .join('; ')
      );
    }
    return trimMessage(JSON.stringify(j.detail));
  } catch {
    return raw || 'Request failed';
  }
}

export function classifyHttpError(status: number, bodyText: string): ClassifiedError {
  const message = parseFastApiDetail(bodyText);

  if (status === 401 || status === 403) {
    return { kind: 'auth', message, status, retryable: false };
  }
  if (status === 429) {
    return {
      kind: 'server',
      message: message || 'Too many requests. Please wait and try again.',
      status,
      retryable: true,
    };
  }
  if (status >= 500) {
    return {
      kind: 'server',
      message: message || 'The server had a problem. Please try again.',
      status,
      retryable: true,
    };
  }
  if (status >= 400) {
    return { kind: 'client', message, status, retryable: false };
  }
  return { kind: 'unknown', message, status, retryable: false };
}

export function classifyThrownError(err: unknown): ClassifiedError {
  if (isClassifiedError(err)) {
    return err;
  }
  if (err instanceof TypeError) {
    const msg = err.message.toLowerCase();
    if (msg.includes('fetch') || msg.includes('network') || msg.includes('failed to load')) {
      return {
          kind: 'network',
        message: 'Could not reach the server. Check your connection and API URL.',
        retryable: true,
      };
    }
  }
  if (err instanceof Error) {
    if (err.name === 'AbortError') {
      return { kind: 'unknown', message: 'Request was cancelled.', retryable: false };
    }
    return { kind: 'unknown', message: trimMessage(err.message), retryable: true };
  }
  return { kind: 'unknown', message: 'Something went wrong.', retryable: true };
}

export function classifyStreamError(message: string): ClassifiedError {
  return {
    kind: 'stream',
    message: trimMessage(message) || 'The response stream failed.',
    retryable: true,
  };
}

/** Thrown when the SSE payload reports `type: "error"` */
export class StreamingFailedError extends Error {
  readonly classified: ClassifiedError;
  constructor(classified: ClassifiedError) {
    super(classified.message);
    this.classified = classified;
    this.name = 'StreamingFailedError';
  }
}

export function errorKindTitle(kind: ApiErrorKind): string {
  switch (kind) {
    case 'network':
      return 'Connection problem';
    case 'auth':
      return 'Sign-in required';
    case 'client':
      return 'Invalid request';
    case 'server':
      return 'Server error';
    case 'stream':
      return 'Streaming interrupted';
    default:
      return 'Something went wrong';
  }
}
