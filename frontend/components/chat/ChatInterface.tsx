'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Chat, Message, UploadedFile } from '@/lib/types';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { LoadingIndicator } from './LoadingIndicator';
import { useStreamingResponse } from '@/hooks/useStreamingResponse';
import { useFileUpload } from '@/hooks/useFileUpload';
import { pollDocumentsUntilReady } from '@/lib/api';
import { errorKindTitle, type ClassifiedError } from '@/lib/errors';
import { toast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ChatInterfaceProps {
  chat: Chat | null;
  onAddMessage?: (message: Message) => void;
  onUpdateLastMessage?: (
    chatId: string,
    content: string,
    isStreaming?: boolean
  ) => void;
  isLoading?: boolean;
}

function errorBannerClass(kind: ClassifiedError['kind']): string {
  switch (kind) {
    case 'auth':
      return 'border-amber-400/20 bg-amber-400/10 text-amber-100';
    case 'network':
      return 'border-orange-400/20 bg-orange-400/10 text-orange-100';
    case 'client':
      return 'border-yellow-400/20 bg-yellow-400/10 text-yellow-100';
    case 'server':
    case 'stream':
      return 'border-red-400/20 bg-red-400/10 text-red-100';
    default:
      return 'border-white/10 bg-slate-900/80 text-slate-200';
  }
}

export function ChatInterface({
  chat,
  onAddMessage,
  onUpdateLastMessage,
  isLoading = false,
}: ChatInterfaceProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const assistantContentRef = useRef('');
  const streamingChatIdRef = useRef<string | null>(null);
  const lastSyncedAssistantContentRef = useRef('');
  const lastQueryRef = useRef<{
    chatId: string;
    message: string;
    documentIds?: string[];
  } | null>(null);
  const lastToastKeyRef = useRef<string | null>(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const [assistantContent, setAssistantContent] = useState('');
  const [activeDocumentIds, setActiveDocumentIds] = useState<string[]>([]);
  const [isPollingEmbeddings, setIsPollingEmbeddings] = useState(false);
  const { uploadFiles, isUploading } = useFileUpload();

  const { stream, isStreaming, queryError, clearQueryError } = useStreamingResponse({
    onChunk: (chunk) => {
      setAssistantContent((prev) => {
        const next = prev + chunk;
        assistantContentRef.current = next;
        return next;
      });
    },
    onSources: (documentIds) => {
      if (documentIds.length > 0) {
        setActiveDocumentIds(Array.from(new Set(documentIds)));
      }
    },
    onComplete: () => {
      const chatId = streamingChatIdRef.current;
      const finalContent = assistantContentRef.current;
      if (chatId) {
        onUpdateLastMessage?.(chatId, finalContent, false);
      }
      lastSyncedAssistantContentRef.current = finalContent;
      streamingChatIdRef.current = null;
      assistantContentRef.current = '';
      setAssistantContent('');
      lastToastKeyRef.current = null;
    },
    onError: () => {
      streamingChatIdRef.current = null;
      lastSyncedAssistantContentRef.current = '';
      assistantContentRef.current = '';
      setAssistantContent('');
    },
  });

  useEffect(() => {
    if (!queryError) {
      lastToastKeyRef.current = null;
      return;
    }
    const key = `${queryError.kind}:${queryError.status ?? ''}:${queryError.message}`;
    if (lastToastKeyRef.current === key) return;
    lastToastKeyRef.current = key;
    toast({
      variant: 'destructive',
      title: errorKindTitle(queryError.kind),
      description: queryError.message,
    });
  }, [queryError]);

  useEffect(() => {
    const chatId = streamingChatIdRef.current;
    if (!chatId || assistantContent === '') return;
    if (assistantContent === lastSyncedAssistantContentRef.current) return;

    lastSyncedAssistantContentRef.current = assistantContent;
    onUpdateLastMessage?.(chatId, assistantContent, true);
  }, [assistantContent, onUpdateLastMessage]);

  const scrollToBottom = useCallback(() => {
    if (shouldAutoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [shouldAutoScroll]);

  useEffect(() => {
    scrollToBottom();
  }, [chat?.messages, assistantContent, scrollToBottom]);

  const handleScroll = useCallback(() => {
    if (!messagesContainerRef.current) return;

    const { scrollHeight, scrollTop, clientHeight } = messagesContainerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    setShouldAutoScroll(isNearBottom);
  }, []);

  const runStream = useCallback(
    async (chatId: string, message: string, queryDocumentIds: string[] | undefined) => {
      lastQueryRef.current = { chatId, message, documentIds: queryDocumentIds };
      streamingChatIdRef.current = chatId;
      lastSyncedAssistantContentRef.current = '';
      assistantContentRef.current = '';
      setAssistantContent('');
      clearQueryError();
      await stream(message, queryDocumentIds);
    },
    [stream, clearQueryError]
  );

  const handleRetryQuery = useCallback(async () => {
    const ctx = lastQueryRef.current;
    if (!ctx || !chat || chat.id !== ctx.chatId || !ctx.message.trim()) return;
    clearQueryError();
    onUpdateLastMessage?.(ctx.chatId, '', true);
    assistantContentRef.current = '';
    setAssistantContent('');
    await runStream(ctx.chatId, ctx.message, ctx.documentIds);
  }, [chat, clearQueryError, onUpdateLastMessage, runStream]);

  const handleSendMessage = useCallback(
    async (message: string, files?: UploadedFile[]) => {
      if (!chat) return;
      const chatId = chat.id;

      const userMessage: Message = {
        id: `msg-${Date.now()}`,
        chatId,
        role: 'user',
        content: message,
        timestamp: new Date(),
        files,
      };

      onAddMessage?.(userMessage);

      const assistantMessage: Message = {
        id: `msg-${Date.now() + 1}`,
        chatId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      };

      onAddMessage?.(assistantMessage);

      let queryDocumentIds = activeDocumentIds;
      if (files?.length) {
        const rawFiles = files
          .map((f) => f.file)
          .filter((f): f is File => !!f);
        if (rawFiles.length > 0) {
          const uploaded = await uploadFiles(rawFiles);
          if (uploaded.length === 0) {
            const msg = 'Document upload did not complete. Check the file and try again.';
            onUpdateLastMessage?.(chatId, msg, false);
            toast({
              variant: 'destructive',
              title: 'Upload failed',
              description: msg,
            });
            return;
          }
          queryDocumentIds = uploaded.map((f) => f.id);
          setActiveDocumentIds(queryDocumentIds);

          setIsPollingEmbeddings(true);
          try {
            const pollResult = await pollDocumentsUntilReady(queryDocumentIds);
            if (!pollResult.ok) {
              onUpdateLastMessage?.(chatId, pollResult.message, false);
              toast({
                variant: 'destructive',
                title: pollResult.reason === 'timeout' ? 'Processing timeout' : 'Document processing failed',
                description: pollResult.message,
              });
              return;
            }
          } finally {
            setIsPollingEmbeddings(false);
          }
        }
      }

      await runStream(chatId, message, queryDocumentIds);
    },
    [chat, onAddMessage, onUpdateLastMessage, activeDocumentIds, uploadFiles, runStream]
  );

  const statusBanner =
    isUploading ? 'Uploading document…' : isPollingEmbeddings ? 'Processing document…' : null;

  const inputBlocked =
    isStreaming || isLoading || isUploading || isPollingEmbeddings;

  const inputPlaceholder = isPollingEmbeddings
    ? 'Embeddings are processing — query is disabled until ready.'
    : isUploading
      ? 'Upload in progress…'
      : isStreaming || isLoading
        ? 'Please wait…'
        : 'Type your message…';

  if (!chat) {
    return (
      <div className="flex h-full items-center justify-center bg-[#111827] px-6">
        <div className="max-w-md space-y-4 rounded-3xl border border-white/10 bg-slate-900/70 px-8 py-10 text-center shadow-[0_20px_70px_rgba(2,6,23,0.35)]">
          <h2 className="text-2xl font-semibold text-slate-100">
            Start a conversation
          </h2>
          <p className="text-sm leading-6 text-slate-400">
            Create a new chat or select an existing one to begin
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-[#111827]">
      <div
        ref={messagesContainerRef}
        onScroll={handleScroll}
        className={cn(
          'scrollbar-thin flex-1 overflow-y-auto',
          'space-y-0 bg-[radial-gradient(circle_at_top,rgba(34,211,238,0.06),transparent_28%),linear-gradient(180deg,#111827_0%,#0f172a_100%)]'
        )}
      >
        {chat.messages.length === 0 ? (
          <div className="flex h-full items-center justify-center px-6">
            <div className="space-y-4 rounded-3xl border border-white/10 bg-slate-900/60 px-8 py-10 text-center shadow-[0_18px_50px_rgba(2,6,23,0.28)]">
              <h3 className="text-xl font-semibold text-slate-200">
                No messages yet
              </h3>
              <p className="text-sm text-slate-400">
                Start typing to begin the conversation
              </p>
            </div>
          </div>
        ) : (
          <>
            {chat.messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                isStreaming={message.isStreaming}
              />
            ))}

            {isStreaming && <LoadingIndicator />}
          </>
        )}

        <div ref={messagesEndRef} />
      </div>

      {queryError && (
        <div
          className={cn(
            'border-t px-4 py-3 text-sm backdrop-blur',
            errorBannerClass(queryError.kind)
          )}
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0 space-y-1">
              <p className="font-semibold">{errorKindTitle(queryError.kind)}</p>
              <p className="wrap-break-word opacity-95">{queryError.message}</p>
              {queryError.status != null ? (
                <p className="text-xs opacity-70">HTTP {queryError.status}</p>
              ) : null}
            </div>
            <div className="flex shrink-0 gap-2">
              {queryError.retryable ? (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => void handleRetryQuery()}
                  disabled={isStreaming || isLoading}
                >
                  Retry
                </Button>
              ) : null}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="text-current hover:bg-white/10"
                onClick={clearQueryError}
              >
                Dismiss
              </Button>
            </div>
          </div>
        </div>
      )}

      <ChatInput
        onSubmit={handleSendMessage}
        isDisabled={inputBlocked}
        isLoading={inputBlocked}
        statusBanner={statusBanner}
        placeholder={inputPlaceholder}
      />
    </div>
  );
}
