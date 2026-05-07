import { useEffect } from 'react'
import { Navigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { HeartPulse, ShieldCheck, AlertTriangle } from 'lucide-react'

import { mcpOAuthService } from '../services/mcpOAuth'
import { useAuthStore } from '../stores/authStore'

const SCOPE_DESCRIPTIONS: Record<string, string> = {
  read: 'Чтение вашей медицинской истории (документы, анализы, заключения)',
}

export default function OAuthConsent() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const [searchParams] = useSearchParams()
  const req = searchParams.get('req')

  // Not logged in → bounce to /login with full consent URL as next.
  if (!isAuthenticated) {
    const next = `/oauth/consent?req=${encodeURIComponent(req ?? '')}`
    return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />
  }

  if (!req) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white px-4">
        <ErrorCard
          title="Запрос не найден"
          message="В URL отсутствует параметр запроса. Откройте подключение из claude.ai заново."
        />
      </div>
    )
  }

  return <ConsentScreen req={req} />
}

function ConsentScreen({ req }: { req: string }) {
  const infoQuery = useQuery({
    queryKey: ['oauth-consent-info', req],
    queryFn: () => mcpOAuthService.getConsentInfo(req),
    retry: false,
  })

  const decisionMutation = useMutation({
    mutationFn: (decision: 'approve' | 'deny') => mcpOAuthService.submitConsent(req, decision),
    onSuccess: ({ redirect_url }) => {
      window.location.href = redirect_url
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Не удалось сохранить решение')
    },
  })

  useEffect(() => {
    document.title = 'Подтверждение доступа · MedHistory'
  }, [])

  if (infoQuery.isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white px-4">
        <div className="text-[15px] text-gray-500">Загружаем запрос...</div>
      </div>
    )
  }

  if (infoQuery.isError || !infoQuery.data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white px-4">
        <ErrorCard
          title="Запрос недействителен или истёк"
          message="Запросы на подключение действительны 10 минут. Попробуйте начать процесс в claude.ai заново."
        />
      </div>
    )
  }

  const info = infoQuery.data
  const clientLabel = info.client_name || info.client_id

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-[480px] bg-white rounded-2xl border border-gray-200 p-8">
        <div className="flex items-center justify-center gap-2 mb-8">
          <HeartPulse className="w-6 h-6 text-emerald-500" strokeWidth={2} />
          <span className="text-[20px] font-semibold text-gray-900 tracking-tight">MedHistory</span>
        </div>

        <h1 className="text-[24px] font-semibold text-gray-900 tracking-tight text-center mb-2">
          Разрешить доступ?
        </h1>
        <p className="text-[15px] text-gray-500 text-center mb-8">
          <span className="font-medium text-gray-900">{clientLabel}</span> запрашивает
          доступ к вашей медицинской истории.
        </p>

        <div className="space-y-3 mb-8">
          {info.scopes.map((scope) => (
            <div key={scope} className="flex gap-3 items-start p-4 bg-emerald-50 rounded-xl">
              <ShieldCheck className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" strokeWidth={2} />
              <div>
                <div className="text-[14px] font-medium text-gray-900">{scope}</div>
                <div className="text-[13px] text-gray-600 mt-0.5">
                  {SCOPE_DESCRIPTIONS[scope] || 'Без описания'}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="flex gap-3 items-start p-4 bg-amber-50 rounded-xl mb-8">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" strokeWidth={2} />
          <div className="text-[13px] text-gray-700">
            Подключайте только сервисы, которым доверяете. Доступ можно отозвать в любой
            момент в настройках вашего аккаунта.
          </div>
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => decisionMutation.mutate('deny')}
            disabled={decisionMutation.isPending}
            className="flex-1 h-[48px] border border-gray-200 rounded-xl text-[15px] font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            Отклонить
          </button>
          <button
            type="button"
            onClick={() => decisionMutation.mutate('approve')}
            disabled={decisionMutation.isPending}
            className="flex-1 h-[48px] rounded-xl text-[15px] font-medium text-white bg-emerald-500 hover:bg-emerald-600 transition-colors disabled:opacity-50"
          >
            {decisionMutation.isPending ? 'Подключаем...' : 'Разрешить'}
          </button>
        </div>
      </div>
    </div>
  )
}

function ErrorCard({ title, message }: { title: string; message: string }) {
  return (
    <div className="w-full max-w-[400px] text-center">
      <h1 className="text-[24px] font-semibold text-gray-900 tracking-tight mb-2">{title}</h1>
      <p className="text-[15px] text-gray-500">{message}</p>
    </div>
  )
}
