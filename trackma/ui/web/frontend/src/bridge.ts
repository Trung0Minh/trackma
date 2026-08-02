export interface ChannelSignal {
  connect(listener: (value: string) => void): void;
}

export interface ChannelTransport {
  response: ChannelSignal;
  event: ChannelSignal;
  request(requestId: string, command: string, payload: string): void;
}

export interface BridgeEvent<T = unknown> {
  name: string;
  payload: T;
}

interface SuccessResponse<T> {
  id: string;
  ok: true;
  data: T;
}

interface ErrorResponse {
  id: string;
  ok: false;
  error: { code: string; message: string; details?: unknown };
}

type BridgeResponse<T = unknown> = SuccessResponse<T> | ErrorResponse;

interface PendingRequest {
  resolve(value: unknown): void;
  reject(error: BridgeError): void;
  timer: number;
}

export class BridgeError extends Error {
  code: string;
  details?: unknown;

  constructor(code: string, message: string, details?: unknown) {
    super(message);
    this.name = 'BridgeError';
    this.code = code;
    this.details = details;
  }
}

export interface AppBridge {
  call<T = unknown>(command: string, payload?: Record<string, unknown>): Promise<T>;
  subscribe(listener: (event: BridgeEvent) => void): () => void;
}

export class BridgeClient implements AppBridge {
  private pending = new Map<string, PendingRequest>();
  private listeners = new Set<(event: BridgeEvent) => void>();

  constructor(private transport: ChannelTransport) {
    transport.response.connect((encoded) => this.handleResponse(encoded));
    transport.event.connect((encoded) => this.handleEvent(encoded));
  }

  call<T = unknown>(command: string, payload: Record<string, unknown> = {}): Promise<T> {
    const requestId = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
    return new Promise<T>((resolve, reject) => {
      const timer = window.setTimeout(() => {
        this.pending.delete(requestId);
        reject(new BridgeError('TIMEOUT', `The ${command} request timed out`));
      }, 30_000);
      this.pending.set(requestId, {
        resolve: (value) => resolve(value as T),
        reject,
        timer,
      });
      this.transport.request(requestId, command, JSON.stringify(payload));
    });
  }

  subscribe(listener: (event: BridgeEvent) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private handleResponse(encoded: string) {
    const response = JSON.parse(encoded) as BridgeResponse;
    const pending = this.pending.get(response.id);
    if (!pending) return;
    window.clearTimeout(pending.timer);
    this.pending.delete(response.id);
    if (response.ok) {
      pending.resolve(response.data);
    } else {
      pending.reject(
        new BridgeError(response.error.code, response.error.message, response.error.details),
      );
    }
  }

  private handleEvent(encoded: string) {
    const event = JSON.parse(encoded) as BridgeEvent;
    this.listeners.forEach((listener) => listener(event));
  }
}

declare global {
  interface Window {
    qt?: { webChannelTransport: unknown };
    QWebChannel?: new (
      transport: unknown,
      callback: (channel: { objects: { trackmaBridge: ChannelTransport } }) => void,
    ) => void;
  }
}

async function loadWebChannelScript() {
  if (window.QWebChannel) return true;
  return new Promise<boolean>((resolve) => {
    const script = document.createElement('script');
    script.src = 'qrc:///qtwebchannel/qwebchannel.js';
    script.onload = () => resolve(Boolean(window.QWebChannel));
    script.onerror = () => resolve(false);
    document.head.append(script);
  });
}

export async function connectNativeBridge(): Promise<BridgeClient | null> {
  if (!window.qt?.webChannelTransport) {
    return Promise.resolve(null);
  }
  if (!(await loadWebChannelScript()) || !window.QWebChannel) return null;
  return new Promise((resolve) => {
    new window.QWebChannel!(window.qt!.webChannelTransport, (channel) => {
      resolve(new BridgeClient(channel.objects.trackmaBridge));
    });
  });
}
