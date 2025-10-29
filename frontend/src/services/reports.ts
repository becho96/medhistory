import api from '../lib/api'
import type { Report, ReportFilters } from '../types'

interface GenerateReportResponse {
  report_id: string
  status: string
  message: string
}

export const reportsService = {
  async generateReport(filters: ReportFilters): Promise<GenerateReportResponse> {
    const response = await api.post<GenerateReportResponse>('/reports/generate', {
      filters,
    })
    return response.data
  },

  async getReports(skip = 0, limit = 50): Promise<Report[]> {
    const response = await api.get<Report[]>('/reports/', {
      params: { skip, limit },
    })
    return response.data
  },

  async getReport(id: string): Promise<Report> {
    const response = await api.get<Report>(`/reports/${id}`)
    return response.data
  },

  getDownloadUrl(id: string): string {
    return `${api.defaults.baseURL}/reports/${id}/download`
  },
}

