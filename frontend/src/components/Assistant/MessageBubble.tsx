import ReactMarkdown from 'react-markdown'
import type { AssistantMessage } from '../../services/assistant'

function InlineMarkdown({ content }: { content: string }) {
  return (
    <ReactMarkdown components={{ p: ({ children }) => <>{children}</> }}>
      {content}
    </ReactMarkdown>
  )
}

/** Parses GFM markdown table and returns { head: string[], rows: string[][] } or null */
function parseMarkdownTable(tableBlock: string): { head: string[]; rows: string[][] } | null {
  const lines = tableBlock.trim().split('\n')
  if (lines.length < 2) return null
  const head = lines[0].split('|').map((c) => c.trim()).filter(Boolean)
  const sep = lines[1]
  if (!/^\|[\s\-:|]+\|$/.test(sep)) return null
  const rows: string[][] = []
  for (let i = 2; i < lines.length; i++) {
    const cells = lines[i].split('|').map((c) => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1)
    if (cells.length) rows.push(cells)
  }
  return { head, rows }
}

/** Splits content into text segments and markdown table blocks */
function splitMarkdownWithTables(content: string): Array<{ type: 'markdown' | 'table'; content: string }> {
  // Match: |..| newline |---| newline (|..| newline)*
  const tableRe = /(\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)*)/g
  const result: Array<{ type: 'markdown' | 'table'; content: string }> = []
  let last = 0
  let m
  while ((m = tableRe.exec(content)) !== null) {
    if (m.index > last) {
      result.push({ type: 'markdown', content: content.slice(last, m.index) })
    }
    result.push({ type: 'table', content: m[1] })
    last = m.index + m[1].length
  }
  if (last < content.length) {
    result.push({ type: 'markdown', content: content.slice(last) })
  }
  return result
}

interface Props {
  message: AssistantMessage | { role: 'user' | 'assistant'; content: string; id?: string }
  isStreaming?: boolean
}

const AGENT_LABELS: Record<string, string> = {
  lab_analysis:         '🔬 Анализ лабораторных данных',
  health_history:       '📋 История болезней',
  recommendation:       '🩺 Рекомендации',
  general_qa:           '💬 Общий вопрос',
  health_trends:        '📈 Динамика показателей',
  supervisor:           '🤔 Анализирует...',
}

export default function MessageBubble({ message, isStreaming }: Props) {
  const isUser = message.role === 'user'
  const intent = 'metadata' in message ? (message.metadata?.intent as string) : undefined

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#4A90E2] to-[#3A7BC8] flex items-center justify-center flex-shrink-0 mr-3 mt-1">
          <span className="text-white text-sm">AI</span>
        </div>
      )}

      <div className={`max-w-[75%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
        {!isUser && intent && AGENT_LABELS[intent] && (
          <span className="text-[10px] text-gray-400 px-1">
            {AGENT_LABELS[intent]}
          </span>
        )}

        <div
          className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
            isUser
              ? 'bg-gradient-to-br from-[#4A90E2] to-[#3A7BC8] text-white rounded-tr-sm'
              : 'bg-white border border-gray-100 text-gray-800 shadow-sm rounded-tl-sm'
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0.5
                            prose-headings:text-gray-900 prose-strong:text-gray-900">
              <div className="overflow-x-auto">
                {splitMarkdownWithTables(message.content).map((part, i) =>
                  part.type === 'markdown' ? (
                    <ReactMarkdown key={i}>{part.content}</ReactMarkdown>
                  ) : (
                    (() => {
                      const t = parseMarkdownTable(part.content)
                      if (!t) return <ReactMarkdown key={i}>{part.content}</ReactMarkdown>
                      return (
                        <div key={i} className="my-2 overflow-x-auto">
                          <table className="min-w-full text-sm border border-gray-200">
                            <thead><tr>{t.head.map((h, j) => <th key={j} className="bg-gray-100 px-3 py-2 border border-gray-200 text-left"><InlineMarkdown content={h} /></th>)}</tr></thead>
                            <tbody>{t.rows.map((row, ri) => <tr key={ri}>{row.map((cell, ci) => <td key={ci} className="px-3 py-2 border border-gray-200"><InlineMarkdown content={cell} /></td>)}</tr>)}</tbody>
                          </table>
                        </div>
                      )
                    })()
                  )
                )}
              </div>
              {isStreaming && (
                <span className="inline-block w-1.5 h-4 bg-[#4A90E2] rounded-sm ml-0.5 animate-pulse" />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
