/**
 * WebSocket client for chat completions
 * This replaces the HTTP streaming endpoint with a WebSocket connection
 */

// Build the WebSocket URL for the chat endpoint.
//
// This code runs in the browser, so it must NOT rely on `process.env.SERVER_BASE_URL`
// (that is a server-only variable — it is `undefined` in the browser bundle and its
// value `localhost:8001` would point at the viewer's own machine, not the server).
//
// Instead we derive the target from the host the site is actually served from, and
// connect to the backend's API port (exposed separately from the Next.js port).
// Overrides:
//   - NEXT_PUBLIC_WS_BASE_URL : full base URL, e.g. "wss://deepwiki.example.com" (best for reverse proxies)
//   - NEXT_PUBLIC_API_PORT    : backend port when it differs from the default 8001
const getWebSocketUrl = () => {
  // Explicit public override wins (must be inlined at build time via NEXT_PUBLIC_*).
  const explicitBase = process.env.NEXT_PUBLIC_WS_BASE_URL;
  if (explicitBase) {
    return `${explicitBase.replace(/\/+$/, '').replace(/^http/, 'ws')}/ws/chat`;
  }

  // Browser: use the host currently being viewed, on the backend API port.
  if (typeof window !== 'undefined') {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = process.env.NEXT_PUBLIC_API_PORT || '8001';
    return `${wsProtocol}//${host}:${port}/ws/chat`;
  }

  // Server-side fallback (e.g. SSR); not normally used for a live WebSocket.
  const wsBaseUrl = (process.env.SERVER_BASE_URL || 'http://localhost:8001').replace(/^http/, 'ws');
  return `${wsBaseUrl}/ws/chat`;
};

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  mode?: 'normal' | 'deep_research';
}

export interface ChatCompletionRequest {
  repo_url: string;
  messages: ChatMessage[];
  filePath?: string;
  token?: string;
  type?: string;
  provider?: string;
  model?: string;
  language?: string;
  research_iteration?: number;
  excluded_dirs?: string;
  excluded_files?: string;
}

/**
 * Creates a WebSocket connection for chat completions
 * @param request The chat completion request
 * @param onMessage Callback for received messages
 * @param onError Callback for errors
 * @param onClose Callback for when the connection closes
 * @returns The WebSocket connection
 */
export const createChatWebSocket = (
  request: ChatCompletionRequest,
  onMessage: (message: string) => void,
  onError: (error: Event) => void,
  onClose: () => void
): WebSocket => {
  // Create WebSocket connection
  const ws = new WebSocket(getWebSocketUrl());
  
  // Set up event handlers
  ws.onopen = () => {
    console.log('WebSocket connection established');
    // Send the request as JSON
    ws.send(JSON.stringify(request));
  };
  
  ws.onmessage = (event) => {
    // Call the message handler with the received text
    onMessage(event.data);
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError(error);
  };
  
  ws.onclose = () => {
    console.log('WebSocket connection closed');
    onClose();
  };
  
  return ws;
};

/**
 * Closes a WebSocket connection
 * @param ws The WebSocket connection to close
 */
export const closeWebSocket = (ws: WebSocket | null): void => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.close();
  }
};
