import type { BatchStatusMessage } from '../api/types';

// Resolve a base URL do WebSocket:
// 1. PUBLIC_WS_URL (env, ex: wss://seudominio.com.br) — sobrescreve tudo.
// 2. PUBLIC_API_URL (env) convertido para WS (http->ws, https->wss).
// 3. Em dev: ws://localhost:8000 (frontend e backend em portas diferentes).
// 4. Em prod sem env: deriva do location atual (NPM faz proxy de /ws/ pro backend).
function resolveWsBase(): string {
  const fromEnv = (import.meta.env.PUBLIC_WS_URL as string | undefined)?.replace(
    /\/+$/,
    '',
  );
  if (fromEnv) return fromEnv;

  const apiBase = (import.meta.env.PUBLIC_API_URL as string | undefined)?.replace(
    /\/+$/,
    '',
  );
  if (apiBase) {
    try {
      const url = new URL(apiBase);
      url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${url.protocol}//${url.host}`;
    } catch {
      // Ignora URL inválida e continua com os fallbacks abaixo.
    }
  }

  if (import.meta.env.DEV) return 'ws://localhost:8000';
  if (typeof window !== 'undefined') {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

    // Em ambiente local sem proxy de /ws, evita cair no default da porta 80.
    const isLocalHost = ['localhost', '127.0.0.1', '0.0.0.0'].includes(window.location.hostname);
    const isDefaultHttpPort = !window.location.port || window.location.port === '80';
    if (isLocalHost && isDefaultHttpPort) {
      return `${proto}//${window.location.hostname}:8000`;
    }

    return `${proto}//${window.location.host}`;
  }
  return '';
}

export function createBatchSocket(
  batchId: string,
  token: string,
  onMessage: (data: BatchStatusMessage) => void,
  onError?: (error: Event) => void,
): { close: () => void } {
  const wsBase = resolveWsBase();
  const url = `${wsBase}/ws/proposals/batch/${batchId}/?token=${token}`;

  let ws: WebSocket;
  let reconnectAttempts = 0;
  const maxReconnectAttempts = 5;
  let closed = false;

  function connect() {
    ws = new WebSocket(url);

    ws.onopen = () => {
      reconnectAttempts = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      if (!closed && reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        setTimeout(connect, 1000 * reconnectAttempts);
      }
    };

    ws.onerror = (e) => onError?.(e);
  }

  connect();

  return {
    close: () => {
      closed = true;
      ws?.close();
    },
  };
}
