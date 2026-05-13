import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, FamilyMember, SubscriptionInfo } from '../types'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean

  // Семейные профили
  activeProfileId: string | null
  activeProfile: FamilyMember | null
  familyProfiles: FamilyMember[]

  // Подписка
  subscription: SubscriptionInfo | null

  setAuth: (user: User, token: string) => void
  logout: () => void
  setSubscription: (subscription: SubscriptionInfo | null) => void
  updateUser: (patch: Partial<User>) => void

  // Методы для работы с профилями
  setFamilyProfiles: (profiles: FamilyMember[]) => void
  setActiveProfile: (profileId: string | null) => void
  clearActiveProfile: () => void
  isViewingOwnProfile: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      activeProfileId: null,
      activeProfile: null,
      familyProfiles: [],
      subscription: null,

      setAuth: (user, token) => {
        localStorage.setItem('auth_token', token)
        set({
          user,
          token,
          isAuthenticated: true,
          activeProfileId: user.id,
          activeProfile: null,
          familyProfiles: [],
          subscription: null,
        })
      },

      logout: () => {
        localStorage.removeItem('auth_token')
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          activeProfileId: null,
          activeProfile: null,
          familyProfiles: [],
          subscription: null,
        })
      },

      setSubscription: (subscription) => set({ subscription }),

      updateUser: (patch) => {
        const current = get().user
        if (!current) return
        set({ user: { ...current, ...patch } })
      },
      
      setFamilyProfiles: (profiles) => {
        const state = get()
        const currentActiveId = state.activeProfileId || state.user?.id
        const activeProfile = profiles.find(p => p.id === currentActiveId) || null
        
        set({ 
          familyProfiles: profiles,
          activeProfile
        })
      },
      
      setActiveProfile: (profileId) => {
        const state = get()
        if (!profileId || profileId === state.user?.id) {
          // Переключаемся на свой профиль
          set({ 
            activeProfileId: state.user?.id || null,
            activeProfile: state.familyProfiles.find(p => p.id === state.user?.id) || null
          })
        } else {
          // Переключаемся на профиль члена семьи
          const profile = state.familyProfiles.find(p => p.id === profileId)
          set({ 
            activeProfileId: profileId,
            activeProfile: profile || null
          })
        }
      },
      
      clearActiveProfile: () => {
        const state = get()
        set({ 
          activeProfileId: state.user?.id || null,
          activeProfile: null
        })
      },
      
      isViewingOwnProfile: () => {
        const state = get()
        return !state.activeProfileId || state.activeProfileId === state.user?.id
      }
    }),
    {
      name: 'auth-storage',
    }
  )
)

