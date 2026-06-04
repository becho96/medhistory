import { useState, useEffect, useCallback } from 'react'
import { MessageCircle, X, Send, CheckCircle2 } from 'lucide-react'
import { feedbackService, FeedbackClientMeta } from '../../services/feedback'

const collectClientMeta = (): FeedbackClientMeta => ({
  viewport: {
    width: window.innerWidth,
    height: window.innerHeight,
  },
  screen: {
    width: window.screen.width,
    height: window.screen.height,
  },
  dpr: window.devicePixelRatio,
  language: navigator.language,
  platform: navigator.platform,
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
})

export default function FeedbackWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleClose = useCallback(() => {
    if (submitting) return
    setIsOpen(false)
    setMessage('')
    setSubmitted(false)
    setError(null)
  }, [submitting])

  useEffect(() => {
    if (!isOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isOpen, handleClose])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = message.trim()
    if (!trimmed || submitting) return

    setSubmitting(true)
    setError(null)

    try {
      await feedbackService.submit({
        message: trimmed,
        url: window.location.pathname + window.location.search,
        user_agent: navigator.userAgent,
        client_meta: collectClientMeta(),
      })
      setSubmitted(true)
      setTimeout(() => {
        setIsOpen(false)
        setMessage('')
        setSubmitted(false)
      }, 1800)
    } catch (err) {
      console.error('Failed to submit feedback:', err)
      setError('Не удалось отправить. Попробуйте ещё раз.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        title="Сообщить о проблеме"
        aria-label="Сообщить о проблеме"
        className="fixed bottom-20 right-4 sm:bottom-6 sm:right-6 z-40 w-12 h-12 sm:w-14 sm:h-14 rounded-full bg-emerald-500 text-white shadow-lg hover:bg-emerald-600 hover:shadow-xl active:scale-95 transition-all flex items-center justify-center"
        style={{ marginBottom: 'env(safe-area-inset-bottom)' }}
      >
        <MessageCircle className="w-5 h-5 sm:w-6 sm:h-6" strokeWidth={2} />
      </button>

      {isOpen && (
        <div
          className="fixed inset-0 z-[130] flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm sm:p-4"
          onClick={handleClose}
        >
          <div
            className="w-full sm:max-w-md bg-white rounded-t-2xl sm:rounded-2xl shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
              <h2 className="text-base font-semibold text-gray-900">Обратная связь</h2>
              <button
                type="button"
                onClick={handleClose}
                disabled={submitting}
                className="p-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50"
                aria-label="Закрыть"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {submitted ? (
              <div className="px-5 py-10 flex flex-col items-center gap-3 text-center">
                <CheckCircle2 className="w-12 h-12 text-emerald-500" strokeWidth={1.5} />
                <p className="text-sm font-medium text-gray-900">Спасибо!</p>
                <p className="text-xs text-gray-500">Мы прочитаем каждое обращение.</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="px-5 py-4 space-y-3">
                <p className="text-xs text-gray-500">
                  Опишите проблему или предложение. К сообщению автоматически прикладываются текущая страница и параметры устройства — это помогает нам разобраться.
                </p>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Что случилось?"
                  rows={5}
                  maxLength={5000}
                  required
                  autoFocus
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent resize-none"
                />
                <div className="flex items-center justify-between gap-3">
                  <span className="text-[11px] text-gray-400">
                    {message.length}/5000
                  </span>
                  <button
                    type="submit"
                    disabled={submitting || !message.trim()}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white text-sm font-medium rounded-lg hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <Send className="w-4 h-4" />
                    {submitting ? 'Отправка…' : 'Отправить'}
                  </button>
                </div>
                {error && (
                  <p className="text-xs text-red-600">{error}</p>
                )}
              </form>
            )}
          </div>
        </div>
      )}
    </>
  )
}
