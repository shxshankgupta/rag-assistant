// API Configuration
// Set NEXT_PUBLIC_API_URL to your FastAPI backend URL
// If not set, the app will run in demo mode with mock data
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;
export const DEMO_MODE = !API_BASE_URL;
export const API_TOKEN = process.env.NEXT_PUBLIC_API_TOKEN;

// Chat constants
export const DEFAULT_CHAT_TITLE = 'New Chat';
export const MESSAGE_SUBMIT_TIMEOUT = 30000; // 30 seconds
export const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20MB
export const ALLOWED_FILE_TYPES = ['application/pdf'];

// UI Constants
export const SIDEBAR_WIDTH = 260;
export const TYPING_INDICATOR_DELAY = 600; // ms before showing typing indicator
export const AUTO_SCROLL_THRESHOLD = 100; // pixels from bottom to auto-scroll

// Messages
export const ERROR_MESSAGES = {
  FILE_TOO_LARGE: 'File is too large. Maximum size is 20MB.',
  FILE_TYPE_NOT_ALLOWED: 'File type is not allowed.',
  NETWORK_ERROR: 'Network error. Please try again.',
  STREAM_ERROR: 'Error streaming response. Please try again.',
  CHAT_CREATE_ERROR: 'Failed to create chat.',
  CHAT_DELETE_ERROR: 'Failed to delete chat.',
  API_NOT_CONFIGURED: 'API URL not configured. Set NEXT_PUBLIC_API_URL environment variable. Running in demo mode.',
};

export const SUCCESS_MESSAGES = {
  FILE_UPLOADED: 'File uploaded successfully.',
  CHAT_CREATED: 'Chat created successfully.',
  CHAT_DELETED: 'Chat deleted successfully.',
};

// Design tokens
export const COLORS = {
  BACKGROUND: '#0d0d0d',
  SURFACE: '#1a1a1a',
  SURFACE_ALT: '#2a2a2a',
  TEXT_PRIMARY: '#ffffff',
  TEXT_SECONDARY: '#a0a0a0',
  ACCENT: '#0ea5e9', // cyan
  ACCENT_HOVER: '#06b6d4',
  BORDER: '#353535',
  USER_MESSAGE_BG: '#1a1a1a',
  ASSISTANT_MESSAGE_BG: '#2a2a2a',
};

// Animation durations (ms)
export const ANIMATION_DURATION = {
  FAST: 150,
  NORMAL: 300,
  SLOW: 500,
};
