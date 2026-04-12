import { useState, useEffect, useRef, useCallback } from 'react'
import { useAuthStore } from '../stores/authStore'
import SessionSidebar from '../components/Assistant/SessionSidebar'
import ChatWindow from '../components/Assistant/ChatWindow'
import {
  AssistantWebSocket,
  fetchSessions,
  fetchMessages,
  deleteSession,
  type AssistantSession,
  type AssistantMessage,
  type ModelConfig,
} from '../services/assistant'
import { loadSavedModelConfig } from '../components/Assistant/ModelSelector'

export default function AssistantPage() {
  const { token } = useAuthStore()

  // Session list
  const [sessions, setSessions] = useState<AssistantSession[]>([])
  const [sessionsLoading, setSessionsLoading] = useState(true)

  // Active session
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<AssistantMessage[]>([])

  // Chat state
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [thinkingAgent, setThinkingAgent] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Model selection (persisted to localStorage)
  const [modelConfig, setModelConfig] = useState<ModelConfig>(loadSavedModelConfig)

  // WebSocket ref (persisted across renders)
  const wsRef = useRef<AssistantWebSocket | null>(null)

  // ── Load sessions ──────────────────────────────────────────────────────────
  const loadSessions = useCallback(async () => {
    if (!token) return
    try {
      const data = await fetchSessions(token)
      setSessions(data)
    } catch {
      // ignore
    } finally {
      setSessionsLoading(false)
    }
  }, [token])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  // ── Load messages for selected session ────────────────────────────────────
  const loadMessages = useCallback(async (sessionId: string) => {
    if (!token) return
    try {
      const data = await fetchMessages(token, sessionId)
      setMessages(data)
    } catch {
      setMessages([])
    }
  }, [token])

  const selectSession = useCallback((id: string) => {
    setActiveSessionId(id)
    loadMessages(id)
    setStreamingContent('')
    setThinkingAgent(null)
  }, [loadMessages])

  const startNewChat = useCallback(() => {
    setActiveSessionId(null)
    setMessages([])
    setStreamingContent('')
    setThinkingAgent(null)
    setInput('')
  }, [])

  // ── WebSocket setup ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!token) return

    const ws = new AssistantWebSocket(token)
    wsRef.current = ws

    ws.connect(
      // onToken
      (token) => setStreamingContent((prev) => prev + token),

      // onThinking
      (agent) => setThinkingAgent(agent),

      // onDone
      (_messageId, _intent) => {
        setStreaming(false)
        setThinkingAgent(null)
        setErrorMessage(null)
        // Reload messages and session list to reflect saved data
        const currentSessionId = activeSessionIdRef.current
        if (currentSessionId) {
          loadMessages(currentSessionId)
        }
        loadSessions()
        setStreamingContent('')
      },

      // onError
      (detail) => {
        setStreaming(false)
        setThinkingAgent(null)
        setStreamingContent('')
        setErrorMessage(detail || 'Произошла ошибка при обработке запроса')
      },

      // onSession
      (newSessionId) => {
        setActiveSessionId(newSessionId)
        activeSessionIdRef.current = newSessionId
      },
    ).catch(() => {
      // Connection failed — will show error on send
    })

    return () => {
      ws.disconnect()
    }
  }, [token]) // Only reconnect if token changes

  // Ref to capture current activeSessionId inside stable callbacks
  const activeSessionIdRef = useRef<string | null>(null)
  useEffect(() => {
    activeSessionIdRef.current = activeSessionId
  }, [activeSessionId])

  // ── Send message ───────────────────────────────────────────────────────────
  const sendMessage = useCallback(() => {
    const text = input.trim()
    if (!text || streaming || !wsRef.current) return

    // Optimistically add user message to UI
    const tempUserMsg: AssistantMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: text,
      metadata: {},
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, tempUserMsg])
    setInput('')
    setStreaming(true)
    setStreamingContent('')
    setThinkingAgent(null)
    setErrorMessage(null)

    wsRef.current.send(text, activeSessionIdRef.current ?? undefined, modelConfig)
  }, [input, streaming, modelConfig])

  // ── Delete session ─────────────────────────────────────────────────────────
  const handleDeleteSession = useCallback(async (id: string) => {
    if (!token) return
    await deleteSession(token, id)
    setSessions((prev) => prev.filter((s) => s.id !== id))
    if (activeSessionId === id) {
      startNewChat()
    }
  }, [token, activeSessionId, startNewChat])

  return (
    <div className="flex h-full -m-4 sm:-m-6 md:-m-8">
      {/* Sidebar — desktop only */}
      <div className="hidden lg:flex flex-col w-72 flex-shrink-0 h-full">
        <SessionSidebar
          sessions={sessions}
          activeId={activeSessionId}
          onSelect={selectSession}
          onNew={startNewChat}
          onDelete={handleDeleteSession}
          loading={sessionsLoading}
        />
      </div>

      {/* Chat area */}
      <div className="flex-1 min-w-0 h-full">
        <ChatWindow
          messages={messages}
          input={input}
          onInputChange={setInput}
          onSend={sendMessage}
          streaming={streaming}
          streamingContent={streamingContent}
          thinkingAgent={thinkingAgent}
          modelConfig={modelConfig}
          onModelChange={setModelConfig}
          sessionId={activeSessionId}
          errorMessage={errorMessage}
        />
      </div>
    </div>
  )
}
