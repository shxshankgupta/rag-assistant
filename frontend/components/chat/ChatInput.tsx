'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Paperclip, Send, X } from 'lucide-react';
import { UploadedFile } from '@/lib/types';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  onSubmit: (message: string, files?: UploadedFile[]) => Promise<void> | void;
  onFileUpload?: (files: UploadedFile[]) => void;
  isDisabled?: boolean;
  isLoading?: boolean;
  placeholder?: string;
  statusBanner?: string | null;
}

export function ChatInput({
  onSubmit,
  onFileUpload,
  isDisabled = false,
  isLoading = false,
  placeholder = 'Type your message...',
  statusBanner = null,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [input, setInput] = useState('');
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
  }, [input]);

  const handleKeyDown = async (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      await handleSubmit();
    }
  };

  const handleSubmit = async () => {
    if (!input.trim() || isDisabled || isLoading) return;
    await onSubmit(input, files.length > 0 ? files : undefined);
    setInput('');
    setFiles([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    processFiles(droppedFiles);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    processFiles(selectedFiles);
  };

  const processFiles = (fileList: File[]) => {
    const uploadedFiles: UploadedFile[] = fileList.map((file) => ({
      id: `${file.name}-${Date.now()}`,
      name: file.name,
      type: file.type,
      size: file.size,
      file,
    }));
    setFiles((prev) => [...prev, ...uploadedFiles]);
    onFileUpload?.(uploadedFiles);
  };

  const removeFile = (fileId: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  return (
    <div className="space-y-3 border-t border-white/10 bg-[#111827]/95 px-4 py-4 backdrop-blur">
      {statusBanner ? (
        <div className="flex items-center gap-2 rounded-xl border border-cyan-400/20 bg-cyan-400/10 px-3 py-2 text-sm text-cyan-100">
          <span className="inline-block size-2 animate-pulse rounded-full bg-cyan-300" />
          {statusBanner}
        </div>
      ) : null}

      {files.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {files.map((file) => (
            <div
              key={file.id}
              className="flex items-center gap-2 rounded-full border border-white/10 bg-slate-900/90 px-3 py-1.5 text-xs text-slate-300"
            >
              <Paperclip size={12} />
              <span className="max-w-32 truncate">{file.name}</span>
              <button
                onClick={() => removeFile(file.id)}
                className="ml-1 rounded-full text-slate-400 transition-colors hover:text-slate-100"
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      <div
        className={cn(
          'flex items-end gap-3 rounded-2xl border border-white/10 bg-slate-900/90 p-3 shadow-[0_10px_30px_rgba(2,6,23,0.28)] transition-colors',
          isDragging && 'border-cyan-400/40 bg-cyan-400/5'
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileInputChange}
          className="hidden"
          disabled={isDisabled || isLoading}
        />

        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={isDisabled || isLoading}
          className="flex-shrink-0 rounded-xl p-2 text-slate-400 transition-colors hover:bg-white/[0.06] hover:text-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
          title="Attach file"
        >
          <Paperclip size={18} />
        </button>

        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isDisabled || isLoading}
          rows={1}
          className={cn(
            'flex-1 resize-none bg-transparent text-slate-100 placeholder:text-slate-500 outline-none',
            'max-h-48 text-sm leading-relaxed'
          )}
        />

        <button
          onClick={handleSubmit}
          disabled={isDisabled || isLoading || !input.trim()}
          className={cn(
            'flex-shrink-0 rounded-xl p-2.5 transition-all',
            input.trim() && !isDisabled && !isLoading
              ? 'bg-slate-200 text-slate-950 shadow-sm hover:bg-white'
              : 'cursor-not-allowed bg-slate-800 text-slate-500'
          )}
          title="Send message"
        >
          <Send size={18} />
        </button>
      </div>

      <p className="text-center text-xs text-slate-500">
        Press <kbd className="rounded-md border border-white/10 bg-slate-900 px-2 py-0.5 text-slate-300">Enter</kbd> to send, <kbd className="rounded-md border border-white/10 bg-slate-900 px-2 py-0.5 text-slate-300">Shift + Enter</kbd> for new line
      </p>
    </div>
  );
}
