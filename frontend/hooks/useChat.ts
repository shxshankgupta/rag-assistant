'use client';

import { useState, useCallback } from 'react';
import { Chat, Message } from '@/lib/types';
import { DEFAULT_CHAT_TITLE } from '@/lib/constants';

// Demo mock data generator
function generateMockChat(title: string = DEFAULT_CHAT_TITLE): Chat {
  return {
    id: `chat-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`,
    title,
    messages: [],
    createdAt: new Date(),
    updatedAt: new Date(),
  };
}

export function useChat() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChat, setActiveChat] = useState<Chat | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchChats = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setIsLoading(false);
    return chats;
  }, [chats]);

  const createChat = useCallback(async (title?: string) => {
    setIsLoading(true);
    setError(null);

    const newChat = generateMockChat(title);

    setChats((prev) => [newChat, ...prev]);
    setActiveChat(newChat);

    setIsLoading(false);
    return newChat;
  }, []);

  const deleteChat = useCallback(
    async (chatId: string) => {
      setError(null);

      setChats((prev) => prev.filter((c) => c.id !== chatId));
      setActiveChat((prev) => (prev?.id === chatId ? null : prev));

      return true;
    },
    []
  );

  const addMessage = useCallback((message: Message) => {
    const updatedAt = new Date();
    const applyUpdate = (chat: Chat): Chat => ({
      ...chat,
      messages: [...chat.messages, message],
      updatedAt,
    });

    setChats((prevChats) =>
      prevChats.map((chat) =>
        chat.id === message.chatId ? applyUpdate(chat) : chat
      )
    );

    setActiveChat((prevActiveChat) => {
      if (!prevActiveChat || prevActiveChat.id !== message.chatId) {
        return prevActiveChat;
      }

      return applyUpdate(prevActiveChat);
    });
  }, []);

  const updateLastMessage = useCallback(
    (chatId: string, content: string, isStreaming: boolean = false) => {
      const updatedAt = new Date();
      const applyUpdate = (chat: Chat): Chat => {
        if (chat.messages.length === 0) {
          return chat;
        }

        const messages = [...chat.messages];
        const lastIndex = messages.length - 1;
        const lastMessage = messages[lastIndex];

        if (
          lastMessage.content === content &&
          lastMessage.isStreaming === isStreaming
        ) {
          return chat;
        }

        messages[lastIndex] = {
          ...lastMessage,
          content,
          isStreaming,
        };

        return {
          ...chat,
          messages,
          updatedAt,
        };
      };

      setChats((prevChats) =>
        prevChats.map((chat) => (chat.id === chatId ? applyUpdate(chat) : chat))
      );

      setActiveChat((prevActiveChat) => {
        if (!prevActiveChat || prevActiveChat.id !== chatId) {
          return prevActiveChat;
        }

        return applyUpdate(prevActiveChat);
      });
    },
    []
  );

  const selectChat = useCallback((chat: Chat) => {
    setActiveChat(chat);
  }, []);

  return {
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
  };
}
