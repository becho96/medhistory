import { useEffect, useRef } from 'react'
import { AlertCircle, Bot, Loader2 } from 'lucide-react'
import MessageBubble from './MessageBubble'
import ChatInput from './ChatInput'
import ModelSelector from './ModelSelector'
import type { AssistantMessage, ModelConfig } from '../../services/assistant'

interface StreamingMessage {
  role: 'assistant'
  content: string
  id?: string
}

interface Props {
  messages: (AssistantMessage | StreamingMessage)[]
  input: string
  onInputChange: (v: string) => void
  onSend: () => void
  streaming: boolean
  streamingContent: string
  thinkingAgent: string | null
  modelConfig: ModelConfig
  onModelChange: (cfg: ModelConfig) => void
  sessionId: string | null
  errorMessage: string | null
}

const AGENT_LABELS: Record<string, string> = {
  supervisor:   'Анализирую вопрос',
  lab_analysis: 'Изучаю анализы',
  health_history: 'Просматриваю историю болезней',
  recommendation: 'Формирую рекомендации',
  general_qa:   'Готовлю ответ',
}

export default function ChatWindow({
  messages, input, onInputChange, onSend, streaming, streamingContent,
  thinkingAgent, modelConfig, onModelChange, sessionId, errorMessage,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  const isEmpty = messages.length === 0 && !streaming

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-white/80 backdrop-blur-sm flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#4A90E2] to-[#3A7BC8] flex items-center justify-center">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">Медицинский ассистент</p>
            <p className="text-[10px] text-gray-400">
              {sessionId ? 'Продолжаем диалог' : 'Новый диалог'}
            </p>
          </div>
        </div>
        <ModelSelector
          value={modelConfig}
          onChange={onModelChange}
          disabled={streaming}
        />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full text-center max-w-md mx-auto">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#4A90E2]/10 to-[#3A7BC8]/10
              border border-[#4A90E2]/20 flex items-center justify-center mb-4">
              <Bot className="w-8 h-8 text-[#4A90E2]" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Медицинский ИИ-ассистент</h3>
            <p className="text-sm text-gray-500 leading-relaxed mb-6">
              Задайте вопрос о вашем здоровье. Я анализирую ваши документы, анализы и историю посещений врачей.
            </p>
            <div className="grid grid-cols-1 gap-2 w-full">
              {[
                'Проанализируй мои последние анализы',
                'Какие у меня хронические заболевания?',
                'К какому врачу мне стоит обратиться?',
                'Как менялся уровень гемоглобина?',
              ].map((hint) => (
                <button
                  key={hint}
                  onClick={() => { onInputChange(hint); }}
                  className="text-left px-4 py-3 rounded-xl border border-gray-200 text-sm text-gray-600
                    hover:border-[#4A90E2]/30 hover:bg-[#4A90E2]/5 transition-colors"
                >
                  {hint}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <MessageBubble
                key={('id' in msg && msg.id) ? msg.id : i}
                message={msg as AssistantMessage}
              />
            ))}

            {/* Streaming message */}
            {streaming && (
              <>
                {thinkingAgent && !streamingContent && (
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#4A90E2] to-[#3A7BC8]
                      flex items-center justify-center flex-shrink-0">
                      <span className="text-white text-sm">AI</span>
                    </div>
                    <div className="flex items-center gap-2 px-4 py-3 bg-white border border-gray-100
                      rounded-2xl rounded-tl-sm shadow-sm">
                      <Loader2 className="w-4 h-4 text-[#4A90E2] animate-spin" />
                      <span className="text-sm text-gray-500">
                        {AGENT_LABELS[thinkingAgent] ?? 'Думаю…'}
                      </span>
                    </div>
                  </div>
                )}
                {streamingContent && (
                  <MessageBubble
                    message={{ role: 'assistant', content: streamingContent }}
                    isStreaming
                  />
                )}
              </>
            )}

            {/* Error message */}
            {errorMessage && !streaming && (
              <div className="flex items-start gap-3 mb-4">
                <div className="w-8 h-8 rounded-full bg-red-100
                  flex items-center justify-center flex-shrink-0">
                  <AlertCircle className="w-4 h-4 text-red-500" />
                </div>
                <div className="px-4 py-3 bg-red-50 border border-red-100
                  rounded-2xl rounded-tl-sm text-sm text-red-700">
                  {errorMessage}
                </div>
              </div>
            )}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex-shrink-0">
        <ChatInput
          value={input}
          onChange={onInputChange}
          onSend={onSend}
          disabled={streaming}
        />
      </div>
    </div>
  )
}
