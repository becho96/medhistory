import api from '../lib/api'
import type {
  PromoCode,
  PromoCodeCreate,
  AdminUserListItem,
  AdminStats,
  User,
} from '../types'

export interface ListPromocodesParams {
  skip?: number
  limit?: number
  is_active?: boolean
}

export interface ListUsersParams {
  skip?: number
  limit?: number
  search?: string
  tier?: 'free' | 'pro'
}

export const adminService = {
  async listPromocodes(params: ListPromocodesParams = {}): Promise<PromoCode[]> {
    const response = await api.get<PromoCode[]>('/admin/promocodes', { params })
    return response.data
  },

  async createPromocode(data: PromoCodeCreate): Promise<PromoCode> {
    const response = await api.post<PromoCode>('/admin/promocodes', data)
    return response.data
  },

  async updatePromocode(id: string, data: { is_active?: boolean; comment?: string }): Promise<PromoCode> {
    const response = await api.patch<PromoCode>(`/admin/promocodes/${id}`, data)
    return response.data
  },

  async deletePromocode(id: string): Promise<void> {
    await api.delete(`/admin/promocodes/${id}`)
  },

  async listUsers(params: ListUsersParams = {}): Promise<AdminUserListItem[]> {
    const response = await api.get<AdminUserListItem[]>('/admin/users', { params })
    return response.data
  },

  async grantPro(userId: string, days: number): Promise<User> {
    const response = await api.post<User>(`/admin/users/${userId}/grant-pro`, { days })
    return response.data
  },

  async revokePro(userId: string): Promise<User> {
    const response = await api.post<User>(`/admin/users/${userId}/revoke-pro`)
    return response.data
  },

  async setAdmin(userId: string, isAdmin: boolean): Promise<User> {
    const response = await api.post<User>(`/admin/users/${userId}/set-admin`, { is_admin: isAdmin })
    return response.data
  },

  async getStats(): Promise<AdminStats> {
    const response = await api.get<AdminStats>('/admin/stats')
    return response.data
  },
}
