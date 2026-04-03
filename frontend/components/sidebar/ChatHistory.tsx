'use client';

import React from 'react';
import { MoreVertical, Plus, Trash2 } from 'lucide-react';
import { Chat } from '@/lib/types';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';

interface ChatHistoryProps {
  chats: Chat[];
  activeChat: Chat | null;
  onSelectChat: (chat: Chat) => void;
  onDeleteChat: (chatId: string) => void;
  onNewChat: () => void;
}

export function ChatHistory({
  chats,
  activeChat,
  onSelectChat,
  onDeleteChat,
  onNewChat,
}: ChatHistoryProps) {
  return (
    <div className="flex h-full flex-col bg-[#020617]">
      <div className="border-b border-white/10 px-4 pb-4 pt-5">
        <div className="mb-4">
          <p className="text-xs font-medium uppercase tracking-[0.24em] text-slate-500">
            Rag Assistant
          </p>
          <h1 className="mt-2 text-lg font-semibold text-slate-100">
            Conversations
          </h1>
        </div>
        <Button
          onClick={onNewChat}
          className="h-11 w-full rounded-xl border border-white/10 bg-slate-800/80 text-slate-100 shadow-sm hover:bg-slate-700/80"
        >
          <Plus size={16} />
          New chat
        </Button>
      </div>

      <div className="scrollbar-thin flex-1 space-y-1 overflow-y-auto p-3">
        {chats.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] px-4 py-10 text-center text-sm text-slate-400">
            No chats yet
          </div>
        ) : (
          chats.map((chat) => (
            <div
              key={chat.id}
              className={cn(
                'group flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2.5 transition-all',
                activeChat?.id === chat.id
                  ? 'border-white/10 bg-slate-800 text-white shadow-sm'
                  : 'border-transparent text-slate-300 hover:border-white/8 hover:bg-white/[0.04] hover:text-slate-100'
              )}
            >
              <button
                onClick={() => onSelectChat(chat)}
                className="flex-1 truncate text-left text-sm transition-colors hover:text-white"
                title={chat.title}
              >
                {chat.title}
              </button>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className={cn(
                      'h-7 w-7 rounded-lg p-0 text-slate-400 opacity-0 transition-all hover:bg-white/[0.06] hover:text-slate-100',
                      activeChat?.id === chat.id && 'opacity-100'
                    )}
                  >
                    <MoreVertical size={14} />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  align="end"
                  className="border-white/10 bg-slate-900 text-slate-100"
                >
                  <DropdownMenuItem
                    onClick={() => onDeleteChat(chat.id)}
                    className="cursor-pointer text-red-300 focus:bg-red-950/40"
                  >
                    <Trash2 size={14} className="mr-2" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
