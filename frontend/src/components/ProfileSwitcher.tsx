import { useState, useEffect, useRef } from 'react'
import { ChevronDown, User, Users, UserPlus, Check, Settings } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { familyService } from '../services/family'
import type { FamilyMember } from '../types'

interface ProfileSwitcherProps {
  onManageFamily?: () => void
}

export default function ProfileSwitcher({ onManageFamily }: ProfileSwitcherProps) {
  const { user, activeProfileId, familyProfiles, setFamilyProfiles, setActiveProfile } = useAuthStore()
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Загружаем профили при монтировании
  useEffect(() => {
    loadProfiles()
  }, [])

  // Закрываем dropdown при клике вне
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const loadProfiles = async () => {
    try {
      setIsLoading(true)
      const profiles = await familyService.getAccessibleProfiles()
      setFamilyProfiles(profiles)
    } catch (error) {
      console.error('Failed to load profiles:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleProfileSelect = (profileId: string) => {
    setActiveProfile(profileId)
    setIsOpen(false)
    // Перезагружаем страницу чтобы данные обновились
    window.location.reload()
  }

  const currentProfile = familyProfiles.find(p => p.id === activeProfileId) || 
    familyProfiles.find(p => p.id === user?.id)

  const isViewingOwnProfile = !activeProfileId || activeProfileId === user?.id

  // Получаем инициалы для аватара
  const getInitials = (name?: string) => {
    if (!name) return '?'
    const parts = name.split(' ')
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase()
    }
    return name.substring(0, 2).toUpperCase()
  }

  // Цвет аватара на основе имени
  const getAvatarColor = (name?: string) => {
    if (!name) return 'from-gray-400 to-gray-500'
    const colors = [
      'from-blue-500 to-blue-600',
      'from-emerald-500 to-emerald-600',
      'from-purple-500 to-purple-600',
      'from-amber-500 to-amber-600',
      'from-rose-500 to-rose-600',
      'from-cyan-500 to-cyan-600',
      'from-indigo-500 to-indigo-600',
    ]
    const index = name.charCodeAt(0) % colors.length
    return colors[index]
  }

  if (familyProfiles.length <= 1 && !onManageFamily) {
    // Если только один профиль (свой) и нет возможности добавить, показываем просто email
    return (
      <div className="flex items-center gap-3 px-4 py-2 rounded-xl bg-gray-50 border border-gray-100">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#4A90E2] to-[#3A7BC8] flex items-center justify-center">
          <User className="w-4 h-4 text-white" />
        </div>
        <span className="text-sm font-medium text-gray-700">{user?.full_name || user?.email}</span>
      </div>
    )
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`
          flex items-center gap-3 px-4 py-2 rounded-xl border transition-all
          ${!isViewingOwnProfile 
            ? 'bg-amber-50 border-amber-200 hover:bg-amber-100' 
            : 'bg-gray-50 border-gray-100 hover:bg-gray-100'
          }
        `}
      >
        <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${getAvatarColor(currentProfile?.full_name)} flex items-center justify-center`}>
          {isViewingOwnProfile ? (
            <User className="w-4 h-4 text-white" />
          ) : (
            <span className="text-xs font-bold text-white">
              {getInitials(currentProfile?.full_name)}
            </span>
          )}
        </div>
        <div className="text-left">
          <div className="text-sm font-medium text-gray-700">
            {currentProfile?.full_name || user?.email || 'Мой профиль'}
          </div>
          {!isViewingOwnProfile && (
            <div className="text-xs text-amber-600">
              {currentProfile?.relation_type_display}
            </div>
          )}
        </div>
        <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-xl border border-gray-100 py-2 z-50">
          {/* Header */}
          <div className="px-4 py-2 border-b border-gray-100">
            <div className="flex items-center gap-2 text-sm font-medium text-gray-500">
              <Users className="w-4 h-4" />
              <span>Профили</span>
            </div>
          </div>

          {/* Profile List */}
          <div className="max-h-64 overflow-y-auto py-2">
            {isLoading ? (
              <div className="px-4 py-3 text-sm text-gray-500 text-center">
                Загрузка...
              </div>
            ) : (
              familyProfiles.map((profile) => {
                const isActive = profile.id === activeProfileId || 
                  (profile.id === user?.id && !activeProfileId)
                const isOwn = profile.id === user?.id

                return (
                  <button
                    key={profile.id}
                    onClick={() => handleProfileSelect(profile.id)}
                    className={`
                      w-full flex items-center gap-3 px-4 py-3 text-left transition-colors
                      ${isActive ? 'bg-blue-50' : 'hover:bg-gray-50'}
                    `}
                  >
                    <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${getAvatarColor(profile.full_name)} flex items-center justify-center flex-shrink-0`}>
                      {isOwn ? (
                        <User className="w-5 h-5 text-white" />
                      ) : (
                        <span className="text-sm font-bold text-white">
                          {getInitials(profile.full_name)}
                        </span>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900 truncate">
                        {profile.full_name || 'Без имени'}
                      </div>
                      <div className="text-xs text-gray-500">
                        {isOwn ? 'Мой профиль' : profile.relation_type_display}
                        {!profile.has_credentials && !isOwn && (
                          <span className="ml-1 text-amber-500">• Нет доступа</span>
                        )}
                      </div>
                    </div>
                    {isActive && (
                      <Check className="w-5 h-5 text-blue-500 flex-shrink-0" />
                    )}
                  </button>
                )
              })
            )}
          </div>

          {/* Footer Actions */}
          {onManageFamily && (
            <div className="border-t border-gray-100 pt-2">
              <button
                onClick={() => {
                  setIsOpen(false)
                  onManageFamily()
                }}
                className="w-full flex items-center gap-3 px-4 py-3 text-left text-sm text-gray-600 hover:bg-gray-50 transition-colors"
              >
                <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center">
                  <UserPlus className="w-5 h-5 text-gray-500" />
                </div>
                <div>
                  <div className="font-medium text-gray-700">Добавить члена семьи</div>
                  <div className="text-xs text-gray-500">Управление семейными профилями</div>
                </div>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

