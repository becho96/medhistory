import api from '../lib/api'
import { 
  HealthEvent, 
  HealthEventCreate, 
  HealthEventsListResponse,
  ParameterDefinition 
} from '../types'

export const healthEventsService = {
  // Библиотека параметров
  getParameterDefinitions: async (primaryOnly: boolean = false): Promise<ParameterDefinition[]> => {
    const response = await api.get('/health-events/parameters', {
      params: { primary_only: primaryOnly }
    })
    return response.data
  },

  // CRUD операции
  getHealthEvents: async (params?: {
    date_from?: string
    date_to?: string
    tags?: string[]
    limit?: number
    offset?: number
  }): Promise<HealthEventsListResponse> => {
    const response = await api.get('/health-events', { params })
    return response.data
  },

  getHealthEvent: async (id: string): Promise<HealthEvent> => {
    const response = await api.get(`/health-events/${id}`)
    return response.data
  },

  createHealthEvent: async (data: HealthEventCreate): Promise<HealthEvent> => {
    const response = await api.post('/health-events', data)
    return response.data
  },

  updateHealthEvent: async (id: string, data: Partial<HealthEventCreate>): Promise<HealthEvent> => {
    const response = await api.patch(`/health-events/${id}`, data)
    return response.data
  },

  deleteHealthEvent: async (id: string): Promise<void> => {
    await api.delete(`/health-events/${id}`)
  }
}
