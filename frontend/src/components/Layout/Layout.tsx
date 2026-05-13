import { Outlet, Link, useLocation } from 'react-router-dom'
import { Home, FileText, BarChart3, LogOut, FlaskConical, Brain, Heart, AlertCircle, Settings, Activity, Plug, Shield, Ticket, Users as UsersIcon } from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'
import { useState, useEffect } from 'react'
import ProfileSwitcher from '../ProfileSwitcher'
import FamilyManagementModal from '../FamilyManagementModal'
import ProfileSettings from '../ProfileSettings'
import { familyService } from '../../services/family'

export default function Layout() {
  const location = useLocation()
  const { user, logout, activeProfileId, activeProfile, setFamilyProfiles } = useAuthStore()
  const [isFamilyModalOpen, setIsFamilyModalOpen] = useState(false)
  const [isProfileSettingsOpen, setIsProfileSettingsOpen] = useState(false)

  const isViewingOwnProfile = !activeProfileId || activeProfileId === user?.id
  const [pendingInvitesCount, setPendingInvitesCount] = useState(0)

  useEffect(() => {
    loadProfiles()
  }, [])

  const loadPendingInvitesCount = () => {
    if (!user) return
    familyService.getPendingInvites()
      .then((invites) => setPendingInvitesCount(invites.length))
      .catch(() => setPendingInvitesCount(0))
  }

  const handlePendingInvitesUpdated = () => {
    loadPendingInvitesCount()
    loadProfiles()
  }

  useEffect(() => {
    loadPendingInvitesCount()
  }, [user, isProfileSettingsOpen])

  const loadProfiles = async () => {
    try {
      const profiles = await familyService.getAccessibleProfiles()
      setFamilyProfiles(profiles)
    } catch (error) {
      console.error('Failed to load profiles:', error)
    }
  }

  const navigation = [
    { name: 'Главная', href: '/', icon: Home },
    { name: 'Медкарта', href: '/documents', icon: FileText },
    { name: 'Анализы', href: '/labs', icon: FlaskConical },
    { name: 'Интеграции', href: '/settings/integrations', icon: Plug },
  ]

  const navigationSoon = [
    { name: 'Самочувствие', href: '/health-events', icon: Activity },
    { name: 'Интерпретации', href: '/interpretations', icon: Brain },
    { name: 'Отчёты', href: '/reports', icon: BarChart3 },
  ]

  const adminNavigation = user?.is_admin
    ? [
        { name: 'Админка', href: '/admin', icon: Shield },
        { name: 'Промокоды', href: '/admin/promocodes', icon: Ticket },
        { name: 'Пользователи', href: '/admin/users', icon: UsersIcon },
      ]
    : []

  return (
    <div className="h-[100dvh] flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md shadow-sm sticky top-0 z-50 border-b border-gray-100"
        style={{ paddingTop: 'env(safe-area-inset-top)' }}
      >
        <div className="max-w-full px-4 sm:px-6 md:px-8">
          <div className="flex justify-between items-center py-3 sm:py-4">
            <div className="flex items-center gap-2 sm:gap-3">
              <Heart className="w-5 h-5 sm:w-6 sm:h-6 text-emerald-500" strokeWidth={2} />
              <h1 className="text-base sm:text-xl font-semibold text-gray-900 tracking-tight">
                MedHistory
              </h1>
            </div>

            <div className="flex items-center gap-2 sm:gap-4">
              <div className="hidden md:block">
                <ProfileSwitcher onManageFamily={() => setIsFamilyModalOpen(true)} />
              </div>
              {isViewingOwnProfile && (
                <button
                  onClick={() => setIsProfileSettingsOpen(true)}
                  className="relative flex items-center gap-1 sm:gap-2 px-2 sm:px-4 py-2 text-xs sm:text-sm font-medium text-gray-600 hover:text-gray-900 rounded-lg sm:rounded-xl hover:bg-gray-50 transition-all"
                  title="Настройки профиля"
                >
                  <span className="relative inline-block">
                    <Settings className="w-4 h-4" />
                    {pendingInvitesCount > 0 && (
                      <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full ring-2 ring-white" />
                    )}
                  </span>
                  <span className="hidden sm:inline">Профиль</span>
                </button>
              )}
              <button
                onClick={logout}
                className="flex items-center gap-1 sm:gap-2 px-2 sm:px-4 py-2 text-xs sm:text-sm font-medium text-gray-600 hover:text-gray-900 rounded-lg sm:rounded-xl hover:bg-gray-50 transition-all"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Выход</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        {/* Sidebar — icon-only on mobile, full on desktop */}
        <aside className="flex flex-col w-14 lg:w-64 bg-white border-r border-gray-100 overflow-y-auto shrink-0">
          <nav className="p-2 lg:p-4 flex-1 space-y-1">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  title={item.name}
                  className={`
                    group flex items-center gap-3 p-2.5 lg:px-3 lg:py-2.5 rounded-xl
                    transition-all duration-150 justify-center lg:justify-start
                    ${isActive
                      ? 'bg-emerald-500 text-white'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    }
                  `}
                >
                  <div className={`
                    w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-all
                    ${isActive ? 'bg-white/20' : 'bg-gray-100 group-hover:bg-gray-200'}
                  `}>
                    <item.icon className={`h-4 w-4 ${isActive ? 'text-white' : 'text-gray-500 group-hover:text-gray-700'}`} />
                  </div>
                  <span className="hidden lg:inline text-sm font-medium">{item.name}</span>
                  {isActive && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-white hidden lg:block" />}
                </Link>
              )
            })}

            <div className="pt-2 lg:pt-3">
              {navigationSoon.map((item) => (
                <div
                  key={item.name}
                  title={item.name}
                  className="flex items-center gap-3 p-2.5 lg:px-3 lg:py-2.5 rounded-xl text-gray-400 cursor-default select-none justify-center lg:justify-start mb-1"
                >
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gray-100 shrink-0">
                    <item.icon className="h-4 w-4 text-gray-400" />
                  </div>
                  <span className="hidden lg:inline text-sm font-medium">{item.name}</span>
                  <span className="ml-auto text-[11px] font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-400 hidden lg:inline">
                    скоро
                  </span>
                </div>
              ))}
            </div>

            {adminNavigation.length > 0 && (
              <div className="pt-3 lg:pt-4 mt-3 border-t border-gray-100">
                <div className="hidden lg:block text-[11px] uppercase font-semibold tracking-wide text-gray-400 px-3 mb-2">
                  Администрирование
                </div>
                {adminNavigation.map((item) => {
                  const isActive = location.pathname === item.href
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      title={item.name}
                      className={`
                        group flex items-center gap-3 p-2.5 lg:px-3 lg:py-2.5 rounded-xl
                        transition-all duration-150 justify-center lg:justify-start mb-1
                        ${isActive
                          ? 'bg-blue-500 text-white'
                          : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                        }
                      `}
                    >
                      <div className={`
                        w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-all
                        ${isActive ? 'bg-white/20' : 'bg-gray-100 group-hover:bg-gray-200'}
                      `}>
                        <item.icon className={`h-4 w-4 ${isActive ? 'text-white' : 'text-gray-500 group-hover:text-gray-700'}`} />
                      </div>
                      <span className="hidden lg:inline text-sm font-medium">{item.name}</span>
                    </Link>
                  )
                })}
              </div>
            )}
          </nav>
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-auto min-w-0">
          <div className="p-3 sm:p-6 md:p-8 max-w-7xl mx-auto">
            {!isViewingOwnProfile && activeProfile && (
              <div className="mb-6 p-4 rounded-xl bg-amber-50 border border-amber-200 flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center">
                  <AlertCircle className="w-5 h-5 text-amber-600" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-amber-800">
                    Вы просматриваете профиль: {activeProfile.full_name}
                  </p>
                  <p className="text-xs text-amber-600">
                    {activeProfile.relation_type_display} • Все действия выполняются от имени этого профиля
                  </p>
                </div>
              </div>
            )}
            <Outlet />
          </div>
        </main>
      </div>

      <FamilyManagementModal
        isOpen={isFamilyModalOpen}
        onClose={() => setIsFamilyModalOpen(false)}
        onProfilesUpdated={loadProfiles}
      />

      {isProfileSettingsOpen && user && (
        <ProfileSettings
          user={user}
          onClose={() => setIsProfileSettingsOpen(false)}
          onPendingInvitesUpdated={handlePendingInvitesUpdated}
        />
      )}
    </div>
  )
}
