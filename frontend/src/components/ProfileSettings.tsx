import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { User as UserIcon, Save, X, Users, Check, XCircle, CreditCard, Crown, ChevronRight } from 'lucide-react'
import { authService } from '../services/auth'
import { familyService } from '../services/family'
import { subscriptionService } from '../services/subscription'
import type { User, Gender, FamilyInvite, SubscriptionInfo } from '../types'

interface ProfileSettingsProps {
  user: User
  onClose: () => void
  onPendingInvitesUpdated?: () => void
}

export default function ProfileSettings({ user, onClose, onPendingInvitesUpdated }: ProfileSettingsProps) {
  const queryClient = useQueryClient()
  const [gender, setGender] = useState<Gender | undefined>(user.gender)
  const [fullName, setFullName] = useState(user.full_name || '')
  const [birthDate, setBirthDate] = useState(user.birth_date || '')
  const [pendingInvites, setPendingInvites] = useState<FamilyInvite[]>([])
  const [invitesLoading, setInvitesLoading] = useState(false)

  useEffect(() => {
    familyService.getPendingInvites()
      .then(setPendingInvites)
      .catch(() => setPendingInvites([]))
  }, [])

  const { data: subscription } = useQuery<SubscriptionInfo>({
    queryKey: ['subscription', 'me'],
    queryFn: subscriptionService.getMe,
  })

  const updateMutation = useMutation({
    mutationFn: (data: { full_name?: string; birth_date?: string; gender?: Gender }) =>
      authService.updateUser(data),
    onSuccess: (updatedUser) => {
      // Обновляем кэш текущего пользователя
      queryClient.setQueryData(['current-user'], updatedUser)
      // Показываем уведомление
      alert('✅ Профиль успешно обновлён!')
      onClose()
    },
    onError: (error) => {
      console.error('Ошибка обновления профиля:', error)
      alert('❌ Не удалось обновить профиль')
    },
  })

  const handleAcceptInvite = async (inviteId: string) => {
    try {
      setInvitesLoading(true)
      await familyService.acceptInvite(inviteId)
      setPendingInvites((prev) => prev.filter((i) => i.id !== inviteId))
      onPendingInvitesUpdated?.()
      alert('✅ Вы присоединились к семейному кабинету. Профили обновлены.')
      queryClient.invalidateQueries({ queryKey: ['family-profiles'] })
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : 'Не удалось принять приглашение'
      alert(`❌ ${msg}`)
    } finally {
      setInvitesLoading(false)
    }
  }

  const handleDeclineInvite = async (inviteId: string) => {
    try {
      setInvitesLoading(true)
      await familyService.declineInvite(inviteId)
      setPendingInvites((prev) => prev.filter((i) => i.id !== inviteId))
      onPendingInvitesUpdated?.()
    } catch {
      alert('❌ Не удалось отклонить приглашение')
    } finally {
      setInvitesLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate({
      full_name: fullName || undefined,
      birth_date: birthDate || undefined,
      gender: gender,
    })
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
              <UserIcon className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Настройки профиля</h2>
              <p className="text-sm text-gray-500">Обновите ваши данные</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            disabled={updateMutation.isPending}
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        {/* Pending family invites */}
        {pendingInvites.length > 0 && (
          <div className="px-6 pt-2 pb-4 border-b border-gray-200">
            <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
              <Users className="w-4 h-4" />
              Приглашения в семейный кабинет
            </h3>
            <p className="text-xs text-gray-500 mb-3">
              Вас пригласили присоединиться к семейному кабинету. Подтвердите или отклоните приглашение.
            </p>
            <div className="space-y-2">
              {pendingInvites.map((invite) => (
                <div
                  key={invite.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-blue-50 border border-blue-100"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {invite.owner_full_name || invite.owner_email || 'Пользователь'}
                    </p>
                    <p className="text-xs text-gray-500">{invite.relation_type_display}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleDeclineInvite(invite.id)}
                      disabled={invitesLoading}
                      className="p-2 rounded-lg text-gray-500 hover:bg-gray-200 hover:text-gray-700 transition-colors disabled:opacity-50"
                      title="Отклонить"
                    >
                      <XCircle className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleAcceptInvite(invite.id)}
                      disabled={invitesLoading}
                      className="p-2 rounded-lg bg-green-600 text-white hover:bg-green-700 transition-colors disabled:opacity-50"
                      title="Принять"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Subscription summary */}
        {subscription && (
          <div className="px-6 pt-4 pb-4 border-b border-gray-200">
            <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
              <CreditCard className="w-4 h-4" />
              Подписка
            </h3>
            <Link
              to="/subscription"
              onClick={onClose}
              className="block p-3 rounded-xl border border-gray-200 hover:border-emerald-300 hover:bg-emerald-50/30 transition-colors group"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  {subscription.tier === 'pro' ? (
                    <div className="w-9 h-9 rounded-lg bg-amber-50 flex items-center justify-center shrink-0">
                      <Crown className="w-4 h-4 text-amber-500" />
                    </div>
                  ) : (
                    <div className="w-9 h-9 rounded-lg bg-gray-100 flex items-center justify-center shrink-0">
                      <CreditCard className="w-4 h-4 text-gray-500" />
                    </div>
                  )}
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-gray-900">
                      {subscription.tier === 'pro' ? 'Pro' : 'Free'}
                    </div>
                    <div className="text-xs text-gray-500">
                      {subscription.used} из {subscription.limit} документов в этом месяце
                    </div>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600 shrink-0" />
              </div>
            </Link>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* Full Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Полное имя
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
              placeholder="Иван Иванов"
            />
          </div>

          {/* Birth Date */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Дата рождения
            </label>
            <input
              type="date"
              value={birthDate}
              onChange={(e) => setBirthDate(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
            />
          </div>

          {/* Gender */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Пол
            </label>
            <p className="text-xs text-gray-500 mb-3">
              Используется для определения референсных значений анализов
            </p>
            <div className="grid grid-cols-3 gap-3">
              <button
                type="button"
                onClick={() => setGender('male')}
                className={`px-4 py-3 rounded-lg border-2 transition-all font-medium ${
                  gender === 'male'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
                }`}
              >
                👨 Мужской
              </button>
              <button
                type="button"
                onClick={() => setGender('female')}
                className={`px-4 py-3 rounded-lg border-2 transition-all font-medium ${
                  gender === 'female'
                    ? 'border-pink-500 bg-pink-50 text-pink-700'
                    : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
                }`}
              >
                👩 Женский
              </button>
              <button
                type="button"
                onClick={() => setGender('other')}
                className={`px-4 py-3 rounded-lg border-2 transition-all font-medium ${
                  gender === 'other'
                    ? 'border-purple-500 bg-purple-50 text-purple-700'
                    : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
                }`}
              >
                ⚧ Другой
              </button>
            </div>
          </div>

          {/* Email (read-only) */}
          {user.email && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email
              </label>
              <input
                type="email"
                value={user.email}
                disabled
                className="w-full px-4 py-2.5 border border-gray-200 rounded-lg bg-gray-50 text-gray-600 cursor-not-allowed"
              />
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={updateMutation.isPending}
              className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={updateMutation.isPending}
              className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {updateMutation.isPending ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                  <span>Сохранение...</span>
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  <span>Сохранить</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
