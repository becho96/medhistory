import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { authService } from '../services/auth'
import { useAuthStore } from '../stores/authStore'
import { HeartPulse } from 'lucide-react'
import { sha256 } from '../lib/sha256'
import { getAttribution, getSourceLabel } from '../lib/attribution'
import { trackGoal } from '../lib/analytics'

interface ConsentVersions {
  terms_and_privacy: string
  special_category: string
}

async function loadConsentVersions(): Promise<ConsentVersions> {
  // Combined hash of terms + privacy (single checkbox), plus separate consent text.
  const [terms, privacy, consent] = await Promise.all([
    fetch('/legal/terms-of-service.md').then((r) => r.text()),
    fetch('/legal/privacy-policy.md').then((r) => r.text()),
    fetch('/legal/consent.md').then((r) => r.text()),
  ])
  return {
    terms_and_privacy: await sha256(terms + '\n---\n' + privacy),
    special_category: await sha256(consent),
  }
}

export default function Register() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((state) => state.setAuth)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [termsAccepted, setTermsAccepted] = useState(false)
  const [consentAccepted, setConsentAccepted] = useState(false)
  const [interviewOptIn, setInterviewOptIn] = useState(false)
  const [versions, setVersions] = useState<ConsentVersions | null>(null)
  const [versionsError, setVersionsError] = useState<string | null>(null)
  const [submitAttempted, setSubmitAttempted] = useState(false)

  useEffect(() => {
    let cancelled = false
    loadConsentVersions()
      .then((v) => !cancelled && setVersions(v))
      .catch((e) => !cancelled && setVersionsError(e.message))
    return () => {
      cancelled = true
    }
  }, [])

  const registerMutation = useMutation({
    mutationFn: async (data: {
      email: string
      password: string
      full_name: string
      consents: ConsentVersions
      signup_utm?: Record<string, string>
      interview_opt_in: boolean
    }) => {
      await authService.register(data)
      const token = await authService.login({ email: data.email, password: data.password })
      localStorage.setItem('auth_token', token.access_token)
      const user = await authService.getCurrentUser()
      return { user, token: token.access_token }
    },
    onSuccess: ({ user, token }) => {
      setAuth(user, token)
      trackGoal('signup', { source: getSourceLabel() })
      toast.success('Добро пожаловать!')
      navigate('/')
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail
      const message =
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
          ? detail.map((e: any) => e.msg).join('; ')
          : 'Ошибка регистрации'
      toast.error(message)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitAttempted(true)
    if (!versions) {
      toast.error('Не удалось загрузить условия — обновите страницу')
      return
    }
    if (!fullName.trim() || !email.trim() || !password.trim()) {
      toast.error('Заполните имя, email и пароль')
      return
    }
    if (!termsAccepted || !consentAccepted) return
    registerMutation.mutate({
      email,
      password,
      full_name: fullName,
      consents: versions,
      signup_utm: getAttribution() ?? undefined,
      interview_opt_in: interviewOptIn,
    })
  }

  const canSubmit =
    !!fullName.trim() &&
    !!email.trim() &&
    !!password.trim() &&
    termsAccepted &&
    consentAccepted &&
    !!versions &&
    !registerMutation.isPending

  return (
    <div className="min-h-screen flex items-center justify-center bg-white px-4 py-8">
      <div className="w-full max-w-[400px]">
        <div className="flex items-center justify-center gap-2 mb-10">
          <HeartPulse className="w-6 h-6 text-emerald-500" strokeWidth={2} />
          <span className="text-[20px] font-semibold text-gray-900 tracking-tight">MedHistory</span>
        </div>

        <div className="text-center mb-8">
          <h1 className="text-[28px] font-semibold text-gray-900 tracking-tight mb-2">
            Создать аккаунт
          </h1>
          <p className="text-[15px] text-gray-500">
            Начните управлять медицинской историей
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="fullName" className="block text-[13px] font-medium text-gray-700 mb-1.5">
              Полное имя
            </label>
            <input
              id="fullName"
              type="text"
              autoComplete="name"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full h-[48px] px-4 border border-gray-200 rounded-xl text-[15px] text-gray-900 placeholder:text-gray-400 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
              placeholder="Иван Иванов"
            />
            {submitAttempted && !fullName.trim() && (
              <p className="mt-1.5 text-[12px] text-red-600">Укажите полное имя</p>
            )}
          </div>

          <div>
            <label htmlFor="email" className="block text-[13px] font-medium text-gray-700 mb-1.5">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full h-[48px] px-4 border border-gray-200 rounded-xl text-[15px] text-gray-900 placeholder:text-gray-400 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
              placeholder="your@email.com"
            />
            {submitAttempted && !email.trim() && (
              <p className="mt-1.5 text-[12px] text-red-600">Укажите email</p>
            )}
          </div>

          <div>
            <label htmlFor="password" className="block text-[13px] font-medium text-gray-700 mb-1.5">
              Пароль
            </label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full h-[48px] px-4 border border-gray-200 rounded-xl text-[15px] text-gray-900 placeholder:text-gray-400 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
              placeholder="••••••••"
            />
            {submitAttempted && !password.trim() && (
              <p className="mt-1.5 text-[12px] text-red-600">Укажите пароль</p>
            )}
          </div>

          <div className="space-y-3 pt-2">
            <label className="flex items-start gap-3 cursor-pointer rounded-xl p-1.5 -m-1.5">
              <input
                type="checkbox"
                checked={termsAccepted}
                onChange={(e) => setTermsAccepted(e.target.checked)}
                className="mt-0.5 w-5 h-5 rounded border-gray-300 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-0"
              />
              <span className="text-[13px] text-gray-600 leading-relaxed">
                Я согласен с{' '}
                <Link to="/legal/terms" target="_blank" className="text-emerald-600 hover:text-emerald-700 underline-offset-2 hover:underline">
                  Пользовательским соглашением
                </Link>
                {' '}и{' '}
                <Link to="/legal/privacy" target="_blank" className="text-emerald-600 hover:text-emerald-700 underline-offset-2 hover:underline">
                  Политикой обработки персональных данных
                </Link>
              </span>
            </label>
            {submitAttempted && !termsAccepted && (
              <p className="text-[12px] text-red-600">Примите пользовательское соглашение и политику обработки данных</p>
            )}

            <label className="flex items-start gap-3 cursor-pointer rounded-xl p-1.5 -m-1.5">
              <input
                type="checkbox"
                checked={consentAccepted}
                onChange={(e) => setConsentAccepted(e.target.checked)}
                className="mt-0.5 w-5 h-5 rounded border-gray-300 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-0"
              />
              <span className="text-[13px] text-gray-600 leading-relaxed">
                Даю{' '}
                <Link to="/legal/consent" target="_blank" className="text-emerald-600 hover:text-emerald-700 underline-offset-2 hover:underline">
                  согласие на обработку данных о состоянии здоровья
                </Link>
                {' '}(спец. категория ПДн по ст. 10 152-ФЗ)
              </span>
            </label>
            {submitAttempted && !consentAccepted && (
              <p className="text-[12px] text-red-600">Подтвердите согласие на обработку данных о здоровье</p>
            )}

            {versionsError && (
              <p className="text-[12px] text-red-600">
                Не удалось загрузить условия. Обновите страницу.
              </p>
            )}
          </div>

          <label className="flex items-start gap-3 cursor-pointer bg-emerald-50 border border-emerald-100 rounded-xl p-3">
            <input
              type="checkbox"
              checked={interviewOptIn}
              onChange={(e) => setInterviewOptIn(e.target.checked)}
              className="mt-0.5 w-5 h-5 rounded border-gray-300 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-0"
            />
            <span className="text-[13px] text-gray-700 leading-relaxed">
              Готов(а) поделиться опытом в коротком интервью (~30 минут).
              Участникам дарим Pro-доступ.
            </span>
          </label>

          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full h-[48px] bg-emerald-500 text-white rounded-xl text-[15px] font-medium hover:bg-emerald-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors mt-2"
          >
            {registerMutation.isPending ? 'Регистрация...' : 'Зарегистрироваться'}
          </button>
        </form>

        <p className="text-center mt-8 text-[14px] text-gray-500">
          Уже есть аккаунт?{' '}
          <Link to="/login" className="font-medium text-emerald-600 hover:text-emerald-700 transition-colors">
            Войти
          </Link>
        </p>
      </div>
    </div>
  )
}
