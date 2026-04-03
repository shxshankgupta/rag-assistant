'use client';

import { useState, useCallback, useRef } from 'react';
import { getApiBaseUrl, refreshAccessToken } from '@/lib/api';
import {
  classifyHttpError,
  classifyStreamError,
  classifyThrownError,
  StreamingFailedError,
  type ClassifiedError,
} from '@/lib/errors';

interface UseStreamingResponseParams {
  onChunk?: (chunk: string) => void;
  onSources?: (documentIds: string[]) => void;
  onComplete?: () => void;
  onError?: (error: ClassifiedError) => void;
}

export function useStreamingResponse({
  onChunk,
  onSources,
  onComplete,
  onError,
}: UseStreamingResponseParams) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [queryError, setQueryError] = useState<ClassifiedError | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const clearQueryError = useCallback(() => {
    setQueryError(null);
  }, []);

  const stream = useCallback(
    async (query: string, documentIds?: string[]) => {
      try {
        setIsStreaming(true);
        setQueryError(null);

        const controller = new AbortController();
        abortControllerRef.current = controller;

        let token =
          typeof window !== 'undefined'
            ? localStorage.getItem('access_token')
            : null;

        const makeRequest = async (currentToken: string | null) =>
          fetch(`${getApiBaseUrl()}/query/stream`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {}),
            },
            body: JSON.stringify({
              query,
              stream: true,
              ...(documentIds?.length ? { document_ids: documentIds } : {}),
            }),
            signal: controller.signal,
          });

        let response = await makeRequest(token);

        if (response.status === 401) {
          try {
            const newToken = await refreshAccessToken();
            response = await makeRequest(newToken);
          } catch (err) {
            const classified = classifyThrownError(err);
            setQueryError(classified);
            onError?.(classified);
            setIsStreaming(false);
            return;
          }
        }

        if (!response.ok) {
          const errorText = await response.text();
          const classified = classifyHttpError(response.status, errorText);
          setQueryError(classified);
          onError?.(classified);
          setIsStreaming(false);
          return;
        }

        const reader = response.body?.getReader();
        if (!reader) {
          const classified: ClassifiedError = {
            kind: 'server',
            message: 'No response body from server.',
            retryable: true,
          };
          setQueryError(classified);
          onError?.(classified);
          setIsStreaming(false);
          return;
        }

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();

          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const rawLine of lines) {
            const line = rawLine.trim();
            if (!line || !line.startsWith('data: ')) continue;

            const payload = line.slice(6).trim();
            if (payload === '[DONE]') continue;

            try {
              const event: {
                type?: string;
                content?: string;
                message?: string;
                sources?: Array<{ document_id: string }>;
              } = JSON.parse(payload);

              if (event.type === 'token' && event.content) {
                onChunk?.(event.content);
              } else if (event.type === 'sources' && Array.isArray(event.sources)) {
                onSources?.(event.sources.map((s) => s.document_id));
              } else if (event.type === 'error') {
                throw new StreamingFailedError(
                  classifyStreamError(String(event.message || 'Streaming error'))
                );
              }
            } catch (err) {
              if (err instanceof StreamingFailedError) {
                throw err;
              }
            }
          }
        }

        setIsStreaming(false);
        onComplete?.();
      } catch (err) {
        if (err instanceof StreamingFailedError) {
          setQueryError(err.classified);
          onError?.(err.classified);
        } else if (err instanceof Error && err.name === 'AbortError') {
          // user cancelled
        } else {
          const classified = classifyThrownError(err);
          setQueryError(classified);
          onError?.(classified);
        }

        setIsStreaming(false);
      }
    },
    [onChunk, onSources, onComplete, onError]
  );

  const cancel = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setIsStreaming(false);
  }, []);

  return {
    stream,
    cancel,
    isStreaming,
    queryError,
    clearQueryError,
  };
}