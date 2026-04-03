'use client';

import React from 'react';
import { Copy, File, Trash2 } from 'lucide-react';
import { Message } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ChatMessageProps {
  message: Message;
  onDelete?: (messageId: string) => void;
  isStreaming?: boolean;
}

export function ChatMessage({
  message,
  onDelete,
  isStreaming,
}: ChatMessageProps) {
  const [copied, setCopied] = React.useState(false);
  const isUser = message.role === 'user';

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatTime = (date: Date) => {
    return new Date(date).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div
      className={cn(
        'message-fade flex gap-4 px-5 py-6',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      {!isUser && (
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border border-white/10 bg-slate-800 text-xs font-semibold text-slate-100 shadow-sm">
          AI
        </div>
      )}

      <div
        className={cn(
          'flex max-w-2xl flex-col gap-2',
          isUser && 'items-end'
        )}
      >
        <div
          className={cn(
            'break-words rounded-2xl border px-4 py-3 shadow-sm backdrop-blur-sm',
            isUser
              ? 'border-slate-700/80 bg-slate-800 text-slate-100'
              : 'border-white/10 bg-slate-800/70 text-slate-100'
          )}
        >
          <p className="text-sm leading-7 whitespace-pre-wrap">
            {message.content}
          </p>
        </div>

        {message.files && message.files.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {message.files.map((file) => (
              <div
                key={file.id}
                className="flex items-center gap-2 rounded-full border border-white/10 bg-slate-900/80 px-3 py-1.5 text-xs text-slate-300"
              >
                <File size={14} />
                <span className="truncate">{file.name}</span>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2 px-1 text-xs text-slate-500">
          <span>{formatTime(message.timestamp)}</span>
          {!isUser && isStreaming ? (
            <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-2 py-0.5 text-[11px] text-cyan-200">
              Streaming
            </span>
          ) : null}
          {!isUser && (
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 rounded-lg p-0 text-slate-400 hover:bg-white/[0.06] hover:text-slate-100"
                onClick={handleCopy}
                title={copied ? 'Copied!' : 'Copy'}
              >
                <Copy size={14} />
              </Button>
              {onDelete && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 rounded-lg p-0 text-slate-400 hover:bg-white/[0.06] hover:text-slate-100"
                  onClick={() => onDelete(message.id)}
                  title="Delete"
                >
                  <Trash2 size={14} />
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      {isUser && (
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border border-slate-700 bg-slate-800 text-xs font-semibold text-slate-100 shadow-sm">
          U
        </div>
      )}
    </div>
  );
}
