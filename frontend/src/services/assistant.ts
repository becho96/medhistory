/**
 * WebSocket service for the AI assistant.
 *
 * Protocol (client → server):
 *   { message: string, session_id?: string, model?: { provider: string, model_id: string } }
 *
 * Protocol (server → client):
 *   { type: "session_created", session_id: string }
 *   { type: "thinking",        agent: string }
 *   { type: "token",           content: string }
 *   { type: "done",            message_id: string, intent: string }
 *   { type: "error",           detail: string }
 */

const WS_BASE = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL.replace(/^http/, 'ws')
  : 'ws://localhost:8000'

export interface ModelConfig {
  provider: string
  model_id: string
}

export interface AssistantSession {
  id: string
  title: string
  model_provider: string
  model_id: string
  created_at: string
  updated_at: string
}

export interface AssistantMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  metadata: Record<string, unknown>
  created_at: string
}

type TokenCallback    = (token: string) => void
type ThinkingCallback = (agent: string) => void
type DoneCallback     = (messageId: string, intent: string) => void
type ErrorCallback    = (detail: string) => void
type SessionCallback  = (sessionId: string) => void

export class AssistantWebSocket {
  private ws: WebSocket | null = null
  private readonly token: string

  private onTokenCb:   TokenCallback    | null = null
  private onThinkingCb: ThinkingCallback | null = null
  private onDoneCb:    DoneCallback     | null = null
  private onErrorCb:   ErrorCallback    | null = null
  private onSessionCb: SessionCallback  | null = null

  constructor(token: string) {
    this.token = token
  }

  connect(
    onToken:   TokenCallback,
    onThinking: ThinkingCallback,
    onDone:    DoneCallback,
    onError:   ErrorCallback,
    onSession: SessionCallback,
  ): Promise<void> {
    this.onTokenCb    = onToken
    this.onThinkingCb = onThinking
    this.onDoneCb     = onDone
    this.onErrorCb    = onError
    this.onSessionCb  = onSession

    return new Promise((resolve, reject) => {
      const url = `${WS_BASE}/api/v1/assistant/ws?token=${encodeURIComponent(this.token)}`
      this.ws = new WebSocket(url)

      this.ws.onopen = () => resolve()

      this.ws.onerror = (_ev) => {
        reject(new Error('WebSocket connection failed'))
        this.onErrorCb?.('Не удалось подключиться к ассистенту')
      }

      this.ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data as string)
          this.handleMessage(data)
        } catch {
          // ignore malformed messages
        }
      }

      this.ws.onclose = () => {
        // Could implement auto-reconnect here
      }
    })
  }

  private handleMessage(data: Record<string, unknown>): void {
    switch (data.type) {
      case 'session_created':
        this.onSessionCb?.(data.session_id as string)
        break
      case 'thinking':
        this.onThinkingCb?.(data.agent as string)
        break
      case 'token':
        this.onTokenCb?.(data.content as string)
        break
      case 'done':
        this.onDoneCb?.(data.message_id as string, data.intent as string)
        break
      case 'error':
        this.onErrorCb?.(data.detail as string)
        break
    }
  }

  send(message: string, sessionId?: string, model?: ModelConfig): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.onErrorCb?.('Соединение не установлено')
      return
    }
    this.ws.send(JSON.stringify({ message, session_id: sessionId, model }))
  }

  disconnect(): void {
    this.ws?.close()
    this.ws = null
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

// ─── REST helpers ──────────────────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
}

export async function fetchSessions(token: string): Promise<AssistantSession[]> {
  const res = await fetch(`${API_BASE}/api/v1/assistant/sessions`, {
    headers: authHeaders(token),
  })
  if (!res.ok) throw new Error('Failed to fetch sessions')
  return res.json()
}

export async function fetchMessages(token: string, sessionId: string): Promise<AssistantMessage[]> {
  const res = await fetch(`${API_BASE}/api/v1/assistant/sessions/${sessionId}/messages`, {
    headers: authHeaders(token),
  })
  if (!res.ok) throw new Error('Failed to fetch messages')
  return res.json()
}

export async function deleteSession(token: string, sessionId: string): Promise<void> {
  await fetch(`${API_BASE}/api/v1/assistant/sessions/${sessionId}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  })
}

export async function fetchAvailableModels(): Promise<Record<string, { id: string; label: string }[]>> {
  const res = await fetch(`${API_BASE}/api/v1/assistant/models`)
  if (!res.ok) throw new Error('Failed to fetch models')
  return res.json()
}
