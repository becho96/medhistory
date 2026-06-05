import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CreditCard, LogOut, Plug, Settings, Shield, Ticket, User, Users } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import ProfileSettings from '../components/ProfileSettings'

export default function Profile() {
  const { user, logout } = useAuthStore()
  const [isProfileSettingsOpen, setIsProfileSettingsOpen] = useState(false)

  if (!user) return null

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-[28px] font-semibold tracking-tight text-gray-900">Профиль</h1>
        <p className="mt-1 text-[14px] text-gray-500">
          Настройки аккаунта и подключений
        </p>
      </div>

      <div className="rounded-2xl border border-gray-100 bg-white p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-50">
            <User className="h-5 w-5 text-emerald-600" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[16px] font-semibold text-gray-900">
              {user.full_name || 'Пользователь'}
            </p>
            {user.email && (
              <p className="truncate text-[13px] text-gray-500">{user.email}</p>
            )}
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white">
        <button
          type="button"
          onClick={() => setIsProfileSettingsOpen(true)}
          className="flex min-h-14 w-full items-center gap-3 border-b border-gray-100 px-4 py-3 text-left"
        >
          <Settings className="h-5 w-5 shrink-0 text-gray-500" />
          <div>
            <p className="text-[15px] font-medium text-gray-900">Настройки профиля</p>
            <p className="text-[12px] text-gray-500">Имя, дата рождения, пол</p>
          </div>
        </button>

        <Link
          to="/settings/integrations"
          className="flex min-h-14 items-center gap-3 border-b border-gray-100 px-4 py-3"
        >
          <Plug className="h-5 w-5 shrink-0 text-gray-500" />
          <div>
            <p className="text-[15px] font-medium text-gray-900">Интеграции</p>
            <p className="text-[12px] text-gray-500">Claude и внешние AI-сервисы через MCP</p>
          </div>
        </Link>

        <Link
          to="/subscription"
          className="flex min-h-14 items-center gap-3 border-b border-gray-100 px-4 py-3"
        >
          <CreditCard className="h-5 w-5 shrink-0 text-gray-500" />
          <div>
            <p className="text-[15px] font-medium text-gray-900">Подписка</p>
            <p className="text-[12px] text-gray-500">Лимиты и Pro-доступ</p>
          </div>
        </Link>

        <Link
          to="/health-events"
          className="flex min-h-14 items-center gap-3 border-b border-gray-100 px-4 py-3"
        >
          <Users className="h-5 w-5 shrink-0 text-gray-500" />
          <div>
            <p className="text-[15px] font-medium text-gray-900">Самочувствие</p>
            <p className="text-[12px] text-gray-500">Симптомы и события здоровья</p>
          </div>
        </Link>

        {user.is_admin && (
          <>
            <Link
              to="/admin"
              className="flex min-h-14 items-center gap-3 border-b border-gray-100 px-4 py-3"
            >
              <Shield className="h-5 w-5 shrink-0 text-gray-500" />
              <div>
                <p className="text-[15px] font-medium text-gray-900">Админка</p>
                <p className="text-[12px] text-gray-500">Служебные разделы</p>
              </div>
            </Link>
            <Link
              to="/admin/promocodes"
              className="flex min-h-14 items-center gap-3 border-b border-gray-100 px-4 py-3"
            >
              <Ticket className="h-5 w-5 shrink-0 text-gray-500" />
              <div>
                <p className="text-[15px] font-medium text-gray-900">Промокоды</p>
                <p className="text-[12px] text-gray-500">Управление промокодами</p>
              </div>
            </Link>
          </>
        )}

        <button
          type="button"
          onClick={logout}
          className="flex min-h-14 w-full items-center gap-3 px-4 py-3 text-left text-red-600"
        >
          <LogOut className="h-5 w-5 shrink-0" />
          <div>
            <p className="text-[15px] font-medium">Выйти</p>
            <p className="text-[12px] text-red-400">Завершить текущую сессию</p>
          </div>
        </button>
      </div>

      {isProfileSettingsOpen && (
        <ProfileSettings
          user={user}
          onClose={() => setIsProfileSettingsOpen(false)}
        />
      )}
    </div>
  )
}
