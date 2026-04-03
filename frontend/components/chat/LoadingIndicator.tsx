'use client';

import React from 'react';

export function LoadingIndicator() {
  return (
    <div className="flex items-center gap-3 px-5 py-3">
      <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border border-white/10 bg-slate-800 text-xs font-semibold text-slate-100 shadow-sm">
        AI
      </div>
      <div className="rounded-full border border-white/10 bg-slate-900/80 px-4 py-3">
        <div className="flex gap-1.5">
          <span className="typing-dot h-1.5 w-1.5 rounded-full bg-slate-400" style={{ animationDelay: '0ms' }} />
          <span className="typing-dot h-1.5 w-1.5 rounded-full bg-slate-400" style={{ animationDelay: '150ms' }} />
          <span className="typing-dot h-1.5 w-1.5 rounded-full bg-slate-400" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
}
