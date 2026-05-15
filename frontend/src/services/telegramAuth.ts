import { api } from '../lib/api'
import { useAuthStore } from '../stores/authStore'
import type { User } from '../types'

/**
 * Exchange Telegram Mini App initData for an authenticated session.
 *
 * The backend validates the initData HMAC signature, returns a JWT for the
 * linked account; we then load the full user and populate the auth store —
 * the same end state as a normal login.
 */
export async function authenticateWithTelegram(initData: string): Promise<void> {
  const { data } = await api.post<{ access_token: string }>('/bot/auth/miniapp', {
    init_data: initData,
  })
  const token = data.access_token

  // Persist the token first so the request interceptor attaches it to /auth/me.
  localStorage.setItem('auth_token', token)

  const { data: user } = await api.get<User>('/auth/me')
  useAuthStore.getState().setAuth(user, token)
}
