import { useEffect, useState } from 'react'
import { X, Download, Trash2, FileText, Calendar, User, Building2, Stethoscope, FlaskConical, Eye } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { format } from 'date-fns'
import { documentsService } from '../../services/documents'
import LabResultsTable from './LabResultsTable'

interface DocumentModalProps {
  documentId: string | null
  onClose: () => void
}

export default function DocumentModal({ documentId, onClose }: DocumentModalProps) {
  const queryClient = useQueryClient()
  const [showLabResults, setShowLabResults] = useState(false)

  // Query for document details
  const { data: doc, isLoading } = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => documentsService.getDocument(documentId!),
    enabled: !!documentId,
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: documentsService.deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      queryClient.invalidateQueries({ queryKey: ['documents-count'] })
      queryClient.invalidateQueries({ queryKey: ['documents-all'] })
      toast.success('Документ удалён')
      onClose()
    },
    onError: () => {
      toast.error('Ошибка при удалении документа')
    },
  })

  const handleDownload = () => {
    if (!doc) return
    const url = documentsService.getDocumentFileUrl(doc.id)
    const link = document.createElement('a')
    link.href = url
    link.download = doc.original_filename
    link.target = '_blank'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const handleOpenFile = async () => {
    if (!doc) return
    try {
      await documentsService.openDocument(doc.id)
    } catch (error) {
      toast.error('Не удалось открыть документ')
    }
  }

  const handleDelete = () => {
    if (!doc) return
    if (window.confirm('Вы уверены, что хотите удалить этот документ?')) {
      deleteMutation.mutate(doc.id)
    }
  }

  // Auto-show lab results if document is a lab result
  useEffect(() => {
    if (doc?.document_type === 'Результаты анализа') {
      setShowLabResults(true)
    } else {
      setShowLabResults(false)
    }
  }, [doc])

  // Close on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose])

  if (!documentId) return null

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div 
        className="bg-white rounded-xl sm:rounded-2xl shadow-2xl max-w-4xl w-full overflow-hidden max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-4 sm:px-6 py-4 sm:py-5 border-b border-gray-100 flex items-center justify-between bg-gradient-to-r from-blue-50 to-white">
          <div className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
            <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0">
              <FileText className="h-5 w-5 sm:h-6 sm:w-6 text-blue-600" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-base sm:text-xl font-semibold text-gray-900 truncate">
                {isLoading ? 'Загрузка...' : doc?.original_filename || 'Документ'}
              </h3>
              {doc?.document_type && (
                <p className="text-xs sm:text-sm text-gray-500 mt-0.5">
                  {doc.document_type}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors flex-shrink-0 ml-2"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 sm:p-6 overflow-y-auto flex-1">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : doc ? (
            <div className="space-y-6">
              {/* Document Info Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Document Date */}
                {doc.document_date && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-gray-500 mb-1">
                      <Calendar className="h-4 w-4" />
                      <span className="text-xs font-medium uppercase tracking-wide">Дата документа</span>
                    </div>
                    <p className="text-sm sm:text-base font-semibold text-gray-900">
                      {format(new Date(doc.document_date), 'dd.MM.yyyy')}
                    </p>
                  </div>
                )}

                {/* Upload Date */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-gray-500 mb-1">
                    <Calendar className="h-4 w-4" />
                    <span className="text-xs font-medium uppercase tracking-wide">Дата загрузки</span>
                  </div>
                  <p className="text-sm sm:text-base font-semibold text-gray-900">
                    {format(new Date(doc.created_at), 'dd.MM.yyyy HH:mm')}
                  </p>
                </div>

                {/* Patient Name */}
                {doc.patient_name && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-gray-500 mb-1">
                      <User className="h-4 w-4" />
                      <span className="text-xs font-medium uppercase tracking-wide">Пациент</span>
                    </div>
                    <p className="text-sm sm:text-base font-semibold text-gray-900">
                      {doc.patient_name}
                    </p>
                  </div>
                )}

                {/* Medical Facility */}
                {doc.medical_facility && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-gray-500 mb-1">
                      <Building2 className="h-4 w-4" />
                      <span className="text-xs font-medium uppercase tracking-wide">Мед. учреждение</span>
                    </div>
                    <p className="text-sm sm:text-base font-semibold text-gray-900">
                      {doc.medical_facility}
                    </p>
                  </div>
                )}

                {/* Specialty */}
                {doc.specialty && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-gray-500 mb-1">
                      <Stethoscope className="h-4 w-4" />
                      <span className="text-xs font-medium uppercase tracking-wide">Специализация</span>
                    </div>
                    <p className="text-sm sm:text-base font-semibold text-gray-900">
                      {doc.specialty}
                    </p>
                  </div>
                )}

                {/* Processing Status */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-gray-500 mb-1">
                    <FileText className="h-4 w-4" />
                    <span className="text-xs font-medium uppercase tracking-wide">Статус обработки</span>
                  </div>
                  <span
                    className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${
                      doc.processing_status === 'completed'
                        ? 'bg-green-100 text-green-700'
                        : doc.processing_status === 'processing'
                        ? 'bg-yellow-100 text-yellow-700'
                        : doc.processing_status === 'failed'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-gray-100 text-gray-700'
                    }`}
                  >
                    {doc.processing_status === 'completed'
                      ? '✓ Обработан'
                      : doc.processing_status === 'processing'
                      ? '⏳ Обработка'
                      : doc.processing_status === 'failed'
                      ? '✗ Ошибка'
                      : '⋯ Ожидание'}
                  </span>
                </div>

                {/* File Info */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-gray-500 mb-1">
                    <FileText className="h-4 w-4" />
                    <span className="text-xs font-medium uppercase tracking-wide">Размер файла</span>
                  </div>
                  <p className="text-sm sm:text-base font-semibold text-gray-900">
                    {(doc.file_size / 1024 / 1024).toFixed(2)} МБ
                  </p>
                </div>
              </div>

              {/* Summary Section */}
              {doc.summary && (
                <div className="border-t border-gray-100 pt-6">
                  <h4 className="text-base sm:text-lg font-semibold text-gray-900 mb-3">
                    📝 Краткое содержание (AI-анализ)
                  </h4>
                  <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-4 sm:p-5">
                    <p className="text-sm sm:text-base text-gray-800 leading-relaxed whitespace-pre-wrap">
                      {doc.summary}
                    </p>
                  </div>
                </div>
              )}

              {/* Lab Results Section */}
              {doc.document_type === 'Результаты анализа' && (
                <div className="border-t border-gray-100 pt-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <FlaskConical className="h-5 w-5 text-purple-600" />
                      <h4 className="text-base sm:text-lg font-semibold text-gray-900">
                        Извлеченные результаты анализов
                      </h4>
                    </div>
                    <button
                      onClick={() => setShowLabResults(!showLabResults)}
                      className="text-xs sm:text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
                    >
                      {showLabResults ? 'Скрыть' : 'Показать'}
                    </button>
                  </div>
                  {showLabResults && (
                    <LabResultsTable
                      documentId={doc.id}
                      documentType={doc.document_type}
                    />
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12">
              <p className="text-gray-500">Документ не найден</p>
            </div>
          )}
        </div>

        {/* Footer */}
        {doc && (
          <div className="px-4 sm:px-6 py-3 sm:py-4 border-t border-gray-100 bg-gray-50 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2 sm:gap-3">
            <div className="flex items-center gap-2 flex-1">
              <button
                onClick={handleOpenFile}
                className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm"
              >
                <Eye className="h-4 w-4" />
                Открыть
              </button>
              <button
                onClick={handleDownload}
                className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium text-sm"
              >
                <Download className="h-4 w-4" />
                Скачать
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Trash2 className="h-4 w-4" />
                Удалить
              </button>
              <button
                onClick={onClose}
                className="flex-1 sm:flex-initial px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium text-sm"
              >
                Закрыть
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

