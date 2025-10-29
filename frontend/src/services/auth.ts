import api from '../lib/api'
import type { LoginCredentials, RegisterData, AuthToken, User } from '../types'

export const authService = {
  async register(data: RegisterData): Promise<User> {
    const response = await api.post<User>('/auth/register', data)
    return response.data
  },

  async login(credentials: LoginCredentials): Promise<AuthToken> {
    const response = await api.post<AuthToken>('/auth/login', credentials)
    return response.data
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/auth/me')
    return response.data
  },
}

