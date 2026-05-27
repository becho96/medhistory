import api from '../lib/api'

export interface FeedbackClientMeta {
  viewport?: { width: number; height: number }
  screen?: { width: number; height: number }
  dpr?: number
  language?: string
  platform?: string
  timezone?: string
}

export interface FeedbackPayload {
  message: string
  url?: string
  user_agent?: string
  client_meta?: FeedbackClientMeta
}

export interface FeedbackResponse {
  id: string
  created_at: string
}

export const feedbackService = {
  submit: async (payload: FeedbackPayload): Promise<FeedbackResponse> => {
    const response = await api.post('/feedback/', payload)
    return response.data
  },
}
