export type MessageRole = 'user' | 'assistant';

export interface UploadedFile {
  id: string;
  name: string;
  type: string;
  size: number;
  url?: string;
  file?: File;
}

export interface Message {
  id: string;
  chatId: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  files?: UploadedFile[];
  isStreaming?: boolean;
}

export interface Chat {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt?: Date;
}

export interface StreamMessage {
  type: 'content' | 'done' | 'error';
  content?: string;
  error?: string;
}
