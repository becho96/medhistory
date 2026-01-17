import { Outlet, Link, useLocation } from 'react-router-dom'
import { Home, FileText, BarChart3, LogOut, FlaskConical, Brain, User, Heart, Menu, X, AlertCircle, Settings } from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'
import { useState, useEffect } from 'react'
import ProfileSwitcher from '../ProfileSwitcher'
import FamilyManagementModal from '../FamilyManagementModal'
import ProfileSettings from '../ProfileSettings'
import { familyService } from '../../services/family'

export default function Layout() {
  const location = useLocation()
  const { user, logout, activeProfileId, activeProfile, setFamilyProfiles } = useAuthStore()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isFamilyModalOpen, setIsFamilyModalOpen] = useState(false)
  const [isProfileSettingsOpen, setIsProfileSettingsOpen] = useState(false)

  const isViewingOwnProfile = !activeProfileId || activeProfileId === user?.id

  // Загружаем профили при монтировании
  useEffect(() => {
    loadProfiles()
  }, [])

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
    { name: 'Интерпретации', href: '/interpretations', icon: Brain },
    { name: 'Отчёты', href: '/reports', icon: BarChart3 },
    { name: 'Анализы', href: '/labs', icon: FlaskConical },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50">
      {/* Modern Header */}
      <header className="bg-white/80 backdrop-blur-md shadow-sm sticky top-0 z-50 border-b border-gray-100">
        <div className="max-w-full px-4 sm:px-6 md:px-8">
          <div className="flex justify-between items-center py-3 sm:py-4">
            <div className="flex items-center gap-2 sm:gap-3">
              {/* Mobile menu button */}
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="lg:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors"
              >
                {isMobileMenuOpen ? (
                  <X className="w-5 h-5 text-gray-600" />
                ) : (
                  <Menu className="w-5 h-5 text-gray-600" />
                )}
              </button>
              
              <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg sm:rounded-xl bg-gradient-to-br from-[#4A90E2] to-[#3A7BC8] flex items-center justify-center shadow-lg shadow-blue-200/50">
                <Heart className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
              </div>
              <div>
                <h1 className="text-base sm:text-xl font-bold bg-gradient-to-r from-[#4A90E2] to-[#3A7BC8] bg-clip-text text-transparent">
                  MedHistory
                </h1>
                <p className="text-xs text-gray-500 hidden sm:block">История болезни</p>
              </div>
            </div>
            <div className="flex items-center gap-2 sm:gap-4">
              <div className="hidden md:block">
                <ProfileSwitcher onManageFamily={() => setIsFamilyModalOpen(true)} />
              </div>
              {isViewingOwnProfile && (
                <button
                  onClick={() => setIsProfileSettingsOpen(true)}
                  className="flex items-center gap-1 sm:gap-2 px-2 sm:px-4 py-2 text-xs sm:text-sm font-medium text-gray-600 hover:text-gray-900 rounded-lg sm:rounded-xl hover:bg-gray-50 transition-all"
                  title="Настройки профиля"
                >
                  <Settings className="w-4 h-4" />
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

      <div className="flex relative">
        {/* Mobile Overlay */}
        {isMobileMenuOpen && (
          <div 
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={() => setIsMobileMenuOpen(false)}
          />
        )}

        {/* Modern Sidebar */}
        <aside className={`
          fixed lg:static inset-y-0 left-0 z-40
          w-72 bg-white/95 lg:bg-white/60 backdrop-blur-sm 
          min-h-[calc(100vh-73px)] lg:min-h-[calc(100vh-73px)]
          border-r border-gray-100
          transform transition-transform duration-300 ease-in-out
          ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          lg:block
          mt-[60px] lg:mt-0
        `}>
          <nav className="p-4 sm:p-6">
            <div className="space-y-2">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    onClick={() => setIsMobileMenuOpen(false)}
                    className={`
                      group flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl
                      transition-all duration-200
                      ${
                        isActive
                          ? 'bg-gradient-to-r from-[#4A90E2] to-[#3A7BC8] text-white shadow-lg shadow-blue-200/50'
                          : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                      }
                    `}
                  >
                    <div className={`
                      w-9 h-9 rounded-lg flex items-center justify-center transition-all
                      ${isActive ? 'bg-white/20' : 'bg-gray-100 group-hover:bg-gray-200'}
                    `}>
                      <item.icon
                        className={`h-5 w-5 ${
                          isActive ? 'text-white' : 'text-gray-500 group-hover:text-gray-700'
                        }`}
                      />
                    </div>
                    <span>{item.name}</span>
                    {isActive && (
                      <div className="ml-auto w-1.5 h-1.5 rounded-full bg-white"></div>
                    )}
                  </Link>
                )
              })}
            </div>

            {/* Sidebar Footer - Health Tip */}
            <div className="mt-6 sm:mt-8 p-3 sm:p-4 rounded-xl bg-gradient-to-br from-[#E8E4F3] to-[#F5F3FF] border border-purple-100">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center flex-shrink-0">
                  <span className="text-lg">💡</span>
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 mb-1">Совет дня</h4>
                  <p className="text-xs text-gray-600 leading-relaxed">
                    Регулярно обновляйте свои медицинские документы для точного мониторинга здоровья
                  </p>
                </div>
              </div>
            </div>

            {/* Mobile User Info & Profile Switcher */}
            <div className="mt-4 md:hidden">
              <ProfileSwitcher onManageFamily={() => {
                setIsMobileMenuOpen(false)
                setIsFamilyModalOpen(true)
              }} />
            </div>
          </nav>
        </aside>

        {/* Main content with padding */}
        <main className="flex-1 p-4 sm:p-6 md:p-8 overflow-auto">
          <div className="max-w-7xl mx-auto">
            {/* Profile Banner - показываем когда просматриваем чужой профиль */}
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

      {/* Family Management Modal */}
      <FamilyManagementModal
        isOpen={isFamilyModalOpen}
        onClose={() => setIsFamilyModalOpen(false)}
        onProfilesUpdated={loadProfiles}
      />

      {/* Profile Settings Modal */}
      {isProfileSettingsOpen && user && (
        <ProfileSettings
          user={user}
          onClose={() => setIsProfileSettingsOpen(false)}
        />
      )}
    </div>
  )
}

