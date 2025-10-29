import api from '../lib/api'
import type { Document } from '../types'

interface DocumentUploadResponse {
  document_id: string
  status: string
  message: string
}

interface GetDocumentsParams {
  skip?: number
  limit?: number
  document_type?: string[]
  patient_name?: string[]
  medical_facility?: string[]
  specialties?: string[]
  document_subtype?: string[]
  research_area?: string[]
  date_from?: string
  date_to?: string
  created_from?: string
  created_to?: string
  sort_by?: 'document_date' | 'created_at'
}

interface FilterValuesResponse {
  field: string
  values: string[]
}

export const documentsService = {
  async uploadDocument(file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post<DocumentUploadResponse>(
      '/documents/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )
    return response.data
  },

  async getDocuments(params?: GetDocumentsParams): Promise<Document[]> {
    // Filter out undefined and empty arrays from params
    const cleanParams: any = {}
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          // For arrays, only include if not empty
          if (Array.isArray(value)) {
            if (value.length > 0) {
              cleanParams[key] = value
            }
          } else {
            cleanParams[key] = value
          }
        }
      })
    }
    
    const response = await api.get<Document[]>('/documents/', { params: cleanParams })
    return response.data
  },

  async getDocument(id: string): Promise<Document> {
    const response = await api.get<Document>(`/documents/${id}`)
    return response.data
  },

  async deleteDocument(id: string): Promise<void> {
    await api.delete(`/documents/${id}`)
  },

  getDocumentFileUrl(id: string): string {
    return `${api.defaults.baseURL}/documents/${id}/file`
  },

  async downloadDocumentFile(id: string): Promise<Blob> {
    const response = await api.get(`/documents/${id}/file`, {
      responseType: 'blob',
    })
    return response.data
  },

  async getDocumentBlobUrl(id: string): Promise<string> {
    const blob = await this.downloadDocumentFile(id)
    return URL.createObjectURL(blob)
  },

  async openDocument(id: string): Promise<void> {
    try {
      const blobUrl = await this.getDocumentBlobUrl(id)
      window.open(blobUrl, '_blank')
      // Clean up blob URL after a delay
      setTimeout(() => URL.revokeObjectURL(blobUrl), 100)
    } catch (error) {
      console.error('Error opening document:', error)
      throw error
    }
  },

  async downloadDocument(id: string, filename: string): Promise<void> {
    try {
      const blob = await this.downloadDocumentFile(id)
      const blobUrl = URL.createObjectURL(blob)
      
      // Create temporary link and trigger download
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      // Clean up
      setTimeout(() => URL.revokeObjectURL(blobUrl), 100)
    } catch (error) {
      console.error('Error downloading document:', error)
      throw error
    }
  },

  async getLabs(documentId: string): Promise<{ lab_results: Array<{ test_name: string; value: string; unit?: string | null; reference_range?: string | null; flag?: string | null }> }> {
    const response = await api.get(`/documents/${documentId}/labs`)
    return { lab_results: response.data.lab_results ?? [] }
  },

  async getLabsSummary(documentId: string): Promise<{ has_labs: boolean; count: number }> {
    const response = await api.get(`/documents/${documentId}/labs/summary`)
    return { has_labs: !!response.data.has_labs, count: response.data.count ?? 0 }
  },

  async listAnalytes(): Promise<{ name: string; count: number }[]> {
    const response = await api.get(`/documents/labs/analytes`)
    return response.data.analytes ?? []
  },

  async getLabTimeSeries(analyte: string): Promise<{ analyte: string; points: Array<{ date?: string; value_num: number; unit?: string | null; document_id?: string; reference_range?: string | null; flag?: string | null }> }> {
    const response = await api.get(`/documents/labs/timeseries`, { params: { analyte } })
    return response.data
  },

  async getFilterValues(field: string, q?: string, limit?: number): Promise<string[]> {
    const response = await api.get<FilterValuesResponse>('/documents/filters/values', {
      params: { field, q, limit }
    })
    return response.data.values
  },

  async getDocumentsCount(params?: Omit<GetDocumentsParams, 'skip' | 'limit' | 'sort_by'>): Promise<number> {
    // Filter out undefined and empty arrays from params
    const cleanParams: any = {}
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          // For arrays, only include if not empty
          if (Array.isArray(value)) {
            if (value.length > 0) {
              cleanParams[key] = value
            }
          } else {
            cleanParams[key] = value
          }
        }
      })
    }
    
    const response = await api.get<{ total: number }>('/documents/count/total', { params: cleanParams })
    return response.data.total
  },
}

