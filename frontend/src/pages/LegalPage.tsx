import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { HeartPulse, ArrowLeft } from 'lucide-react'

const SLUG_TO_FILE: Record<string, { file: string; title: string }> = {
  privacy: { file: 'privacy-policy.md', title: 'Политика обработки персональных данных' },
  terms: { file: 'terms-of-service.md', title: 'Пользовательское соглашение' },
  consent: { file: 'consent.md', title: 'Согласие на обработку персональных данных' },
  processors: { file: 'processors.md', title: 'Перечень обработчиков' },
}

const mdComponents = {
  h1: (props: any) => (
    <h1 className="text-[28px] sm:text-[32px] font-semibold tracking-tight text-gray-900 mt-2 mb-6" {...props} />
  ),
  h2: (props: any) => (
    <h2 className="text-[20px] sm:text-[22px] font-semibold tracking-tight text-gray-900 mt-10 mb-3" {...props} />
  ),
  h3: (props: any) => (
    <h3 className="text-[16px] sm:text-[17px] font-semibold text-gray-900 mt-6 mb-2" {...props} />
  ),
  p: (props: any) => <p className="text-[15px] text-gray-700 leading-relaxed my-3" {...props} />,
  a: (props: any) => (
    <a className="text-emerald-600 hover:text-emerald-700 underline-offset-2 hover:underline" {...props} />
  ),
  ul: (props: any) => <ul className="list-disc pl-6 my-3 text-[15px] text-gray-700 space-y-1.5" {...props} />,
  ol: (props: any) => <ol className="list-decimal pl-6 my-3 text-[15px] text-gray-700 space-y-1.5" {...props} />,
  li: (props: any) => <li className="leading-relaxed" {...props} />,
  strong: (props: any) => <strong className="font-semibold text-gray-900" {...props} />,
  hr: (props: any) => <hr className="my-8 border-gray-200" {...props} />,
  table: (props: any) => (
    <div className="overflow-x-auto my-5">
      <table className="w-full text-[14px] border-collapse" {...props} />
    </div>
  ),
  thead: (props: any) => <thead className="bg-gray-50" {...props} />,
  th: (props: any) => (
    <th className="border border-gray-200 px-3 py-2 text-left font-semibold text-gray-900" {...props} />
  ),
  td: (props: any) => <td className="border border-gray-200 px-3 py-2 align-top text-gray-700" {...props} />,
  code: (props: any) => (
    <code className="bg-gray-100 text-gray-800 rounded px-1 py-0.5 text-[13px]" {...props} />
  ),
}

export default function LegalPage() {
  const { slug } = useParams<{ slug: string }>()
  const meta = slug ? SLUG_TO_FILE[slug] : undefined

  const [content, setContent] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!meta) {
      setError('Документ не найден')
      return
    }
    let cancelled = false
    fetch(`/legal/${meta.file}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.text()
      })
      .then((text) => {
        if (!cancelled) setContent(text)
      })
      .catch((e) => {
        if (!cancelled) setError(`Не удалось загрузить документ: ${e.message}`)
      })
    return () => {
      cancelled = true
    }
  }, [meta])

  if (!meta) {
    return (
      <div className="min-h-screen bg-white px-4 py-12">
        <div className="max-w-[760px] mx-auto text-center">
          <h1 className="text-[24px] font-semibold text-gray-900 mb-4">Документ не найден</h1>
          <Link to="/" className="text-emerald-600 hover:text-emerald-700">На главную</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-gray-100 px-4 sm:px-10 py-4">
        <div className="max-w-[1400px] mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-gray-900">
            <HeartPulse className="w-5 h-5 text-emerald-500" strokeWidth={2} />
            <span className="text-[16px] font-semibold tracking-tight">MedHistory</span>
          </Link>
          <Link
            to="/"
            className="flex items-center gap-1.5 text-[13px] text-gray-500 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            На главную
          </Link>
        </div>
      </header>

      <main className="px-4 sm:px-10 py-10 sm:py-14">
        <article className="max-w-[760px] mx-auto">
          {error ? (
            <p className="text-red-600 text-[15px]">{error}</p>
          ) : content ? (
            <ReactMarkdown components={mdComponents}>{content}</ReactMarkdown>
          ) : (
            <p className="text-gray-400 text-[15px]">Загрузка…</p>
          )}
        </article>
      </main>

      <footer className="border-t border-gray-100 px-4 sm:px-10 py-6 mt-10">
        <div className="max-w-[760px] mx-auto flex flex-wrap items-center gap-x-5 gap-y-2 text-[12px] text-gray-500">
          <Link to="/legal/privacy" className="hover:text-gray-900">Политика</Link>
          <Link to="/legal/terms" className="hover:text-gray-900">Соглашение</Link>
          <Link to="/legal/consent" className="hover:text-gray-900">Согласие</Link>
          <Link to="/legal/processors" className="hover:text-gray-900">Обработчики</Link>
          <span className="text-gray-400">&copy; {new Date().getFullYear()} MedHistory</span>
        </div>
      </footer>
    </div>
  )
}
