import api from '../lib/api'
import type { TimelineResponse } from '../types'

interface TimelineParams {
  specialty?: string
  document_type?: string
  patient_name?: string
  medical_facility?: string
  date_from?: string
  date_to?: string
}

export const timelineService = {
  async getTimeline(params?: TimelineParams): Promise<TimelineResponse> {
    const response = await api.get<TimelineResponse>('/timeline/', { params })
    return response.data
  },

  async getTimelineStats(): Promise<any> {
    const response = await api.get('/timeline/stats')
    return response.data
  },

  async getSuggestions(field: string, q?: string): Promise<string[]> {
    const response = await api.get<{ values: string[] }>('/timeline/suggestions', {
      params: { field, q }
    })
    return response.data.values
  },
}

