import { useRef, useEffect, type KeyboardEvent } from 'react'
import { Send } from 'lucide-react'

interface Props {
  value: string
  onChange: (v: string) => void
  onSend: () => void
  disabled: boolean
  placeholder?: string
}

export default function ChatInput({ value, onChange, onSend, disabled, placeholder }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`
  }, [value])

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!disabled && value.trim()) {
        onSend()
      }
    }
  }

  return (
    <div className="flex items-end gap-2 p-4 border-t border-gray-100 bg-white">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKey}
        disabled={disabled}
        placeholder={placeholder ?? 'Задайте вопрос о вашем здоровье…'}
        rows={1}
        className={`flex-1 resize-none rounded-xl border px-4 py-3 text-sm leading-snug outline-none transition-colors
          ${disabled
            ? 'bg-gray-50 text-gray-400 border-gray-200 cursor-not-allowed'
            : 'bg-white border-gray-200 text-gray-900 focus:border-[#4A90E2] focus:ring-2 focus:ring-[#4A90E2]/20'
          }`}
      />
      <button
        onClick={onSend}
        disabled={disabled || !value.trim()}
        className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all
          ${disabled || !value.trim()
            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
            : 'bg-gradient-to-br from-[#4A90E2] to-[#3A7BC8] text-white shadow-md hover:shadow-lg active:scale-95'
          }`}
      >
        <Send className="w-4 h-4" />
      </button>
    </div>
  )
}
