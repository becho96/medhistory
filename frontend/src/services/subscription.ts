import api from '../lib/api'
import type { SubscriptionInfo, ActivatePromoCodeResponse } from '../types'

export const subscriptionService = {
  async getMe(): Promise<SubscriptionInfo> {
    const response = await api.get<SubscriptionInfo>('/subscription/me')
    return response.data
  },

  async activate(code: string): Promise<ActivatePromoCodeResponse> {
    const response = await api.post<ActivatePromoCodeResponse>('/subscription/activate', { code })
    return response.data
  },
}
