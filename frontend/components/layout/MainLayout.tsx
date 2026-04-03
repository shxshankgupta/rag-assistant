'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from '@/components/sidebar/Sidebar';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { useChat } from '@/hooks/useChat';
import { Message } from '@/lib/types';
import { DEMO_MODE } from '@/lib/constants';

export function MainLayout() {
  const {
    chats,
    activeChat,
    isLoading,
    error,
    fetchChats,
    createChat,
    deleteChat,
    addMessage,
    updateLastMessage,
    selectChat,
  } = useChat();

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    const initChats = async () => {
      await fetchChats();
      setIsInitializing(false);
    };
    initChats();
  }, [fetchChats]);

  const handleNewChat = async () => {
    const newChat = await createChat();
    if (newChat) {
      selectChat(newChat);
      setSidebarOpen(false);
    }
  };

  const handleAddMessage = useCallback((message: Message) => {
    addMessage(message);
  }, [addMessage]);

  const handleUpdateLastMessage = useCallback(
    (chatId: string, content: string, isStreaming: boolean = false) => {
      updateLastMessage(chatId, content, isStreaming);
    },
    [updateLastMessage]
  );

  if (isInitializing) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#0f172a]">
        <div className="space-y-4 rounded-3xl border border-white/10 bg-slate-900/70 px-8 py-10 text-center shadow-[0_20px_70px_rgba(2,6,23,0.35)]">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-b-2 border-t-2 border-cyan-300" />
          <p className="text-slate-400">Loading chats...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#0f172a] text-slate-100">
      <Sidebar
        chats={chats}
        activeChat={activeChat}
        onSelectChat={selectChat}
        onDeleteChat={deleteChat}
        onNewChat={handleNewChat}
        isOpen={sidebarOpen}
        onToggle={setSidebarOpen}
      />

      <div className="flex flex-1 flex-col overflow-hidden bg-[#111827]">
        {DEMO_MODE && (
          <div className="flex items-center gap-2 border-b border-amber-400/15 bg-amber-400/10 px-4 py-3 text-sm text-amber-100 backdrop-blur">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-amber-300" />
            Demo mode active - Set NEXT_PUBLIC_API_URL to connect to your FastAPI backend
          </div>
        )}

        {error && (
          <div className="border-b border-red-400/15 bg-red-400/10 px-4 py-3 text-sm text-red-200 backdrop-blur">
            Error: {error}
          </div>
        )}

        <ChatInterface
          chat={activeChat}
          onAddMessage={handleAddMessage}
          onUpdateLastMessage={handleUpdateLastMessage}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}
