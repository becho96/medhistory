import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CreditCard, Check, AlertCircle, Loader2, Crown, Users, FileText } from 'lucide-react'
import { toast } from 'sonner'
import { subscriptionService } from '../services/subscription'
import { useAuthStore } from '../stores/authStore'
import type { SubscriptionInfo } from '../types'

const PROMO_ERROR_MESSAGES: Record<string, string> = {
  not_found: 'Промокод не найден',
  inactive: 'Промокод деактивирован',
  expired: 'Срок действия промокода истёк',
  exhausted: 'Лимит активаций промокода исчерпан',
  already_used: 'Вы уже активировали этот промокод',
}

function formatExpiry(iso?: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
}

export default function Subscription() {
  const queryClient = useQueryClient()
  const setSubscription = useAuthStore((s) => s.setSubscription)
  const updateUser = useAuthStore((s) => s.updateUser)
  const [code, setCode] = useState('')

  const { data: info, isLoading } = useQuery<SubscriptionInfo>({
    queryKey: ['subscription', 'me'],
    queryFn: subscriptionService.getMe,
  })

  const activateMutation = useMutation({
    mutationFn: (value: string) => subscriptionService.activate(value),
    onSuccess: (data) => {
      toast.success(`Pro активирован до ${formatExpiry(data.activated_until)}`)
      setCode('')
      setSubscription(data.subscription)
      updateUser({ subscription_tier: 'pro', pro_expires_at: data.activated_until })
      queryClient.invalidateQueries({ queryKey: ['subscription', 'me'] })
      queryClient.invalidateQueries({ queryKey: ['current-user'] })
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail
      const reason = typeof detail === 'object' && detail !== null ? detail.reason : null
      toast.error(PROMO_ERROR_MESSAGES[reason as string] || 'Не удалось активировать промокод')
    },
  })

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const value = code.trim()
    if (!value) return
    activateMutation.mutate(value)
  }

  if (isLoading || !info) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    )
  }

  const isPro = info.tier === 'pro'
  const usagePct = info.limit > 0 ? Math.min(100, Math.round((info.used / info.limit) * 100)) : 0
  const isBillingOwner = info.is_billing_owner

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center gap-3">
        <CreditCard className="w-6 h-6 text-emerald-500" />
        <h1 className="text-2xl font-semibold text-gray-900">Подписка</h1>
      </div>

      {!isBillingOwner && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
          <div className="text-sm text-amber-800">
            Ваш месячный лимит документов расходуется владельцем семьи. Вы можете активировать
            собственный промокод — он применится к вашему профилю, когда вы выйдете из семьи.
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-gray-200 bg-white p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-gray-500 mb-1">Текущий тариф</div>
            <div className="flex items-center gap-2">
              {isPro ? (
                <>
                  <Crown className="w-5 h-5 text-amber-500" />
                  <span className="text-xl font-semibold text-gray-900">Pro</span>
                </>
              ) : (
                <span className="text-xl font-semibold text-gray-900">Free</span>
              )}
            </div>
            {isPro && info.pro_expires_at && (
              <div className="text-sm text-gray-500 mt-1">
                Действует до {formatExpiry(info.pro_expires_at)}
              </div>
            )}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-gray-700">Документов в этом месяце</span>
            <span className="font-medium text-gray-900">
              {info.used} из {info.limit}
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-gray-100 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                usagePct >= 100 ? 'bg-red-500' : usagePct >= 80 ? 'bg-amber-500' : 'bg-emerald-500'
              }`}
              style={{ width: `${usagePct}%` }}
            />
          </div>
        </div>
      </div>

      {isBillingOwner && (
        <form onSubmit={onSubmit} className="rounded-2xl border border-gray-200 bg-white p-6 space-y-3">
          <h2 className="text-base font-semibold text-gray-900">Активировать промокод</h2>
          <p className="text-sm text-gray-500">
            Введите промокод, чтобы получить или продлить подписку Pro.
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="Например, EARLYBIRD"
              className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              maxLength={64}
            />
            <button
              type="submit"
              disabled={!code.trim() || activateMutation.isPending}
              className="px-4 py-2 rounded-lg bg-emerald-500 text-white text-sm font-medium hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {activateMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              Активировать
            </button>
          </div>
          <p className="text-xs text-gray-500 pt-1">
            Стоимость Pro — 200 ₽ / мес. Чтобы получить промокод, напишите{' '}
            <a
              href="https://t.me/ironbor15"
              target="_blank"
              rel="noopener noreferrer"
              className="text-emerald-600 hover:text-emerald-700 font-medium"
            >
              @ironbor15
            </a>{' '}
            в Telegram.
          </p>
        </form>
      )}

      <div className="rounded-2xl border border-gray-200 bg-white p-6">
        <div className="flex items-baseline justify-between mb-4 gap-3 flex-wrap">
          <h2 className="text-base font-semibold text-gray-900">Что даёт Pro</h2>
          <div className="text-sm text-gray-600">
            <span className="text-lg font-semibold text-gray-900">200 ₽</span>
            <span className="text-gray-500"> / мес</span>
          </div>
        </div>
        <ul className="space-y-3">
          <li className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
              <FileText className="w-4 h-4 text-emerald-600" />
            </div>
            <div>
              <div className="font-medium text-gray-900">До 100 документов в месяц</div>
              <div className="text-sm text-gray-500">Free-тариф ограничен 2 документами в месяц.</div>
            </div>
          </li>
          <li className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
              <Users className="w-4 h-4 text-emerald-600" />
            </div>
            <div>
              <div className="font-medium text-gray-900">Семейный аккаунт</div>
              <div className="text-sm text-gray-500">
                Добавляйте профили членов семьи и ведите их медицинскую историю в одном месте.
              </div>
            </div>
          </li>
          <li className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
              <Check className="w-4 h-4 text-emerald-600" />
            </div>
            <div>
              <div className="font-medium text-gray-900">Общий пул семьи</div>
              <div className="text-sm text-gray-500">
                Все загрузки членов семьи расходуют единый лимит владельца.
              </div>
            </div>
          </li>
        </ul>
      </div>
    </div>
  )
}
