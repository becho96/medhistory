import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FileText, Download, Plus, Filter } from 'lucide-react'
import { toast } from 'sonner'
import { reportsService } from '../services/reports'
import { format } from 'date-fns'
import type { ReportFilters } from '../types'

export default function Reports() {
  const queryClient = useQueryClient()
  const [showGenerateForm, setShowGenerateForm] = useState(false)
  const [filters, setFilters] = useState<ReportFilters>({})

  const { data: reports, isLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: () => reportsService.getReports(),
  })

  const generateMutation = useMutation({
    mutationFn: reportsService.generateReport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
      toast.success('Отчёт успешно сгенерирован')
      setShowGenerateForm(false)
      setFilters({})
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Ошибка генерации отчёта')
    },
  })

  const handleGenerateReport = () => {
    generateMutation.mutate(filters)
  }

  const handleDownload = (reportId: string) => {
    const url = reportsService.getDownloadUrl(reportId)
    const link = document.createElement('a')
    link.href = url
    link.download = `medical_report_${reportId}.pdf`
    link.target = '_blank'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className="space-y-4 md:space-y-8 page-transition">
      {/* Modern Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 sm:gap-3 mb-2 sm:mb-3">
            <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg sm:rounded-xl bg-gradient-to-br from-green-100 to-emerald-50 flex items-center justify-center shadow-lg shadow-green-200/50">
              <FileText className="h-5 w-5 sm:h-6 sm:w-6 text-green-600" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-900">Отчёты</h1>
            </div>
          </div>
          <p className="text-sm sm:text-base md:text-lg text-gray-600">
            Генерируйте медицинские отчёты для врачей
          </p>
        </div>
        <button
          onClick={() => setShowGenerateForm(!showGenerateForm)}
          className="btn-primary text-sm sm:text-base w-full sm:w-auto"
        >
          <Plus className="h-4 w-4 sm:h-5 sm:w-5" />
          Создать отчёт
        </button>
      </div>

      {/* Generate Report Form */}
      {showGenerateForm && (
        <div className="medical-card bg-gradient-to-br from-blue-50 to-white border border-blue-100">
          <div className="flex items-center gap-2 sm:gap-3 mb-4 sm:mb-6">
            <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <Filter className="h-4 w-4 sm:h-5 sm:w-5 text-blue-600" />
            </div>
            <h3 className="text-base sm:text-xl font-semibold text-gray-900">
              Параметры отчёта
            </h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
            <div>
              <label className="block text-xs sm:text-sm font-semibold text-gray-700 mb-1.5 sm:mb-2">
                👨‍⚕️ Специализация
              </label>
              <input
                type="text"
                value={filters.specialty || ''}
                onChange={(e) =>
                  setFilters({ ...filters, specialty: e.target.value })
                }
                placeholder="Например: гастроэнтеролог"
                className="w-full px-3 sm:px-4 py-2 sm:py-3 text-sm sm:text-base border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#4A90E2] focus:border-[#4A90E2]"
              />
            </div>
            <div>
              <label className="block text-xs sm:text-sm font-semibold text-gray-700 mb-1.5 sm:mb-2">
                📄 Тип документа
              </label>
              <input
                type="text"
                value={filters.document_type || ''}
                onChange={(e) =>
                  setFilters({ ...filters, document_type: e.target.value })
                }
                placeholder="Например: анализ крови"
                className="w-full px-3 sm:px-4 py-2 sm:py-3 text-sm sm:text-base border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#4A90E2] focus:border-[#4A90E2]"
              />
            </div>
            <div>
              <label className="block text-xs sm:text-sm font-semibold text-gray-700 mb-1.5 sm:mb-2">
                📅 Дата от
              </label>
              <input
                type="date"
                value={filters.date_from || ''}
                onChange={(e) =>
                  setFilters({ ...filters, date_from: e.target.value })
                }
                className="w-full px-3 sm:px-4 py-2 sm:py-3 text-sm sm:text-base border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#4A90E2] focus:border-[#4A90E2]"
              />
            </div>
            <div>
              <label className="block text-xs sm:text-sm font-semibold text-gray-700 mb-1.5 sm:mb-2">
                📅 Дата до
              </label>
              <input
                type="date"
                value={filters.date_to || ''}
                onChange={(e) =>
                  setFilters({ ...filters, date_to: e.target.value })
                }
                className="w-full px-3 sm:px-4 py-2 sm:py-3 text-sm sm:text-base border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#4A90E2] focus:border-[#4A90E2]"
              />
            </div>
          </div>
          <div className="mt-4 sm:mt-6 flex items-center justify-end gap-2 sm:gap-3">
            <button
              onClick={() => {
                setShowGenerateForm(false)
                setFilters({})
              }}
              className="px-3 sm:px-5 py-2 sm:py-2.5 border border-gray-200 rounded-lg text-xs sm:text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Отмена
            </button>
            <button
              onClick={handleGenerateReport}
              disabled={generateMutation.isPending}
              className="px-3 sm:px-5 py-2 sm:py-2.5 bg-[#4A90E2] text-white rounded-lg text-xs sm:text-sm font-medium hover:bg-[#3A7BC8] disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-lg shadow-blue-200/50"
            >
              {generateMutation.isPending
                ? '⏳ Генерация...'
                : '✨ Сгенерировать отчёт'}
            </button>
          </div>
        </div>
      )}

      {/* Reports List */}
      <div className="medical-card">
        <div className="pb-4 sm:pb-6 mb-4 sm:mb-6 border-b border-gray-100">
          <h3 className="text-base sm:text-xl font-semibold text-gray-900">
            📋 Сгенерированные отчёты ({reports?.length || 0})
          </h3>
        </div>
        <div className="space-y-3 sm:space-y-4">
          {isLoading ? (
            <div className="py-12 sm:py-16 text-center">
              <div className="animate-spin rounded-full h-10 w-10 sm:h-12 sm:w-12 border-b-2 border-[#4A90E2] mx-auto mb-3 sm:mb-4"></div>
              <p className="text-xs sm:text-sm text-gray-600">Загрузка отчётов...</p>
            </div>
          ) : reports && reports.length > 0 ? (
            reports.map((report) => (
              <div key={report.id} className="p-3 sm:p-4 bg-gray-50 hover:bg-gray-100 rounded-lg sm:rounded-xl transition-all border border-transparent hover:border-[#4A90E2]/20">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div className="flex items-start gap-2 sm:gap-4 flex-1 min-w-0">
                    <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg sm:rounded-xl bg-white flex items-center justify-center flex-shrink-0">
                      <FileText className="h-5 w-5 sm:h-6 sm:w-6 text-green-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm sm:text-base font-semibold text-gray-900 mb-1 sm:mb-2">
                        📄 Медицинский отчёт
                      </p>
                      <div className="flex flex-col sm:flex-row sm:flex-wrap gap-x-4 sm:gap-x-6 gap-y-1 text-xs sm:text-sm text-gray-600">
                        <div className="flex items-center gap-1">
                          <span className="font-medium text-gray-500">Создан:</span>
                          <span>{format(new Date(report.created_at), 'dd.MM.yyyy, HH:mm')}</span>
                        </div>
                        {report.report_type && (
                          <div className="flex items-center gap-1">
                            <span className="font-medium text-gray-500">Тип:</span>
                            <span>
                              {report.report_type === 'specialty_summary'
                                ? 'По специализации'
                                : 'Полная история'}
                            </span>
                          </div>
                        )}
                        {report.file_size && (
                          <div className="flex items-center gap-1">
                            <span className="font-medium text-gray-500">Размер:</span>
                            <span>{(report.file_size / 1024).toFixed(2)} КБ</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex-shrink-0">
                    <button
                      onClick={() => handleDownload(report.id)}
                      className="inline-flex items-center justify-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-1.5 sm:py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium text-xs sm:text-sm transition-colors shadow-lg shadow-green-200/50 w-full sm:w-auto"
                    >
                      <Download className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                      Скачать
                    </button>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="py-12 sm:py-16 text-center">
              <div className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4 rounded-full bg-green-100 flex items-center justify-center">
                <FileText className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
              <h3 className="text-sm sm:text-base font-semibold text-gray-900 mb-2">
                Нет отчётов
              </h3>
              <p className="text-xs sm:text-sm text-gray-500 mb-4 sm:mb-6 px-4">
                Создайте ваш первый медицинский отчёт
              </p>
              <button
                onClick={() => setShowGenerateForm(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium text-xs sm:text-sm transition-colors shadow-lg shadow-green-200/50"
              >
                <Plus className="h-4 w-4 sm:h-5 sm:w-5" />
                Создать отчёт
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

