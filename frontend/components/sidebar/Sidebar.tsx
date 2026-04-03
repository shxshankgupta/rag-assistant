'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { LogOut, Menu, ShieldCheck, X } from 'lucide-react';
import { Chat } from '@/lib/types';
import { ChatHistory } from './ChatHistory';
import { Button } from '@/components/ui/button';
import { SIDEBAR_WIDTH } from '@/lib/constants';
import { clearTokens } from '@/lib/auth';

interface SidebarProps {
  chats: Chat[];
  activeChat: Chat | null;
  onSelectChat: (chat: Chat) => void;
  onDeleteChat: (chatId: string) => void;
  onNewChat: () => void;
  isOpen?: boolean;
  onToggle?: (open: boolean) => void;
}

export function Sidebar({
  chats,
  activeChat,
  onSelectChat,
  onDeleteChat,
  onNewChat,
  isOpen = true,
  onToggle,
}: SidebarProps) {
  const router = useRouter();

  const handleLogout = () => {
    clearTokens();
    onToggle?.(false);
    router.replace('/login');
  };

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        className="fixed left-4 top-4 z-40 border border-white/10 bg-slate-950/90 text-slate-200 shadow-lg backdrop-blur md:hidden hover:bg-slate-900"
        onClick={() => onToggle?.(!isOpen)}
      >
        {isOpen ? <X size={20} /> : <Menu size={20} />}
      </Button>

      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-slate-950/70 backdrop-blur-sm md:hidden"
          onClick={() => onToggle?.(false)}
        />
      )}

      <div
        className={`fixed left-0 top-0 z-40 flex h-screen w-60 flex-col border-r border-white/10 bg-[#020617] transition-transform duration-300 md:relative md:h-full md:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        style={{ width: SIDEBAR_WIDTH }}
      >
        <div className="flex-1 overflow-hidden">
          <ChatHistory
            chats={chats}
            activeChat={activeChat}
            onSelectChat={(chat) => {
              onSelectChat(chat);
              onToggle?.(false);
            }}
            onDeleteChat={onDeleteChat}
            onNewChat={onNewChat}
          />
        </div>

        <div className="border-t border-white/10 px-4 py-4">
          <div className="mb-3 rounded-2xl border border-white/10 bg-white/[0.03] px-3 py-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-800 text-slate-100">
                <ShieldCheck size={18} />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-100">Authenticated</p>
                <p className="text-xs text-slate-400">Session is active</p>
              </div>
            </div>
          </div>

          <Button
            type="button"
            variant="ghost"
            className="h-11 w-full justify-start rounded-xl border border-white/10 bg-white/[0.03] px-3 text-slate-200 hover:bg-white/[0.06] hover:text-white"
            onClick={handleLogout}
          >
            <LogOut size={16} />
            Logout
          </Button>
        </div>
      </div>
    </>
  );
}
