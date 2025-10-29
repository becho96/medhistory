import api from '../lib/api'
import type { Interpretation, InterpretationCreate, InterpretationList } from '../types'

export const interpretationsService = {
  /**
   * Создать новую интерпретацию для выбранных документов
   */
  async createInterpretation(data: InterpretationCreate): Promise<Interpretation> {
    const response = await api.post<Interpretation>('/interpretations/', data)
    return response.data
  },

  /**
   * Получить список всех интерпретаций пользователя
   */
  async getInterpretations(skip: number = 0, limit: number = 100): Promise<InterpretationList> {
    const response = await api.get<InterpretationList>('/interpretations/', {
      params: { skip, limit }
    })
    return response.data
  },

  /**
   * Получить конкретную интерпретацию по ID
   */
  async getInterpretation(id: string): Promise<Interpretation> {
    const response = await api.get<Interpretation>(`/interpretations/${id}`)
    return response.data
  },

  /**
   * Удалить интерпретацию
   */
  async deleteInterpretation(id: string): Promise<void> {
    await api.delete(`/interpretations/${id}`)
  },
}

