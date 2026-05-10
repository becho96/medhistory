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
  const [activeTab, setActiveTab] = useState<'info' | 'labs'>('info')
  const [summaryExpanded, setSummaryExpanded] = useState(false)

  const { data: doc, isLoading } = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => documentsService.getDocument(documentId!),
    enabled: !!documentId,
  })

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
    const targetWindow = window.open('', '_blank')
    try {
      await documentsService.openDocument(doc.id, targetWindow)
    } catch {
      toast.error('Не удалось открыть документ')
    }
  }

  const handleDelete = () => {
    if (!doc) return
    if (window.confirm('Вы уверены, что хотите удалить этот документ?')) {
      deleteMutation.mutate(doc.id)
    }
  }

  useEffect(() => {
    setSummaryExpanded(false)
  }, [documentId])

  useEffect(() => {
    if (doc) setActiveTab(doc.document_type === 'Результаты анализа' ? 'labs' : 'info')
  }, [doc?.id, doc?.document_type])

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose])

  if (!documentId) return null

  const isLabResult = doc?.document_type === 'Результаты анализа'

  const statusLabel = (s: string) => ({
    completed: { text: '✓ Обработан', color: 'text-green-600' },
    processing: { text: '⏳ Обработка', color: 'text-yellow-600' },
    failed:     { text: '✗ Ошибка',    color: 'text-red-600' },
  }[s] ?? { text: '⋯ Ожидание', color: 'text-gray-500' })

  return (
    <div
      className="fixed inset-0 z-[110] flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm sm:p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl max-w-4xl w-full overflow-hidden max-h-[92vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-gray-100 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-50 flex items-center justify-center shrink-0">
            <FileText className="h-4 w-4 text-emerald-500" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm sm:text-base font-semibold text-gray-900 truncate">
              {isLoading ? 'Загрузка...' : doc?.original_filename || 'Документ'}
            </h3>
            {doc?.document_type && (
              <p className="text-xs text-gray-500">{doc.document_type}</p>
            )}
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-gray-400 shrink-0">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tabs — only for lab results */}
        {isLabResult && (
          <div className="flex border-b border-gray-100 px-4 bg-white shrink-0">
            <button
              onClick={() => setActiveTab('info')}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'info' ? 'border-emerald-500 text-emerald-600' : 'border-transparent text-gray-500'
              }`}
            >
              Информация
            </button>
            <button
              onClick={() => setActiveTab('labs')}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'labs' ? 'border-emerald-500 text-emerald-600' : 'border-transparent text-gray-500'
              }`}
            >
              <FlaskConical className="w-3.5 h-3.5" />
              Анализы
            </button>
          </div>
        )}

        {/* Content */}
        <div className="overflow-y-auto flex-1">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-500" />
            </div>
          ) : doc ? (
            <>
              {/* Info tab */}
              {(!isLabResult || activeTab === 'info') && (
                <div className="p-4 sm:p-6 space-y-4">
                  {/* Compact metadata rows */}
                  <div className="bg-gray-50 rounded-xl overflow-hidden divide-y divide-gray-100">
                    {doc.document_date && (
                      <div className="flex items-center gap-3 px-3 py-2.5">
                        <Calendar className="w-4 h-4 text-gray-400 shrink-0" />
                        <span className="text-xs text-gray-500 w-28 shrink-0">Дата документа</span>
                        <span className="text-sm font-medium text-gray-900 flex-1 text-right">
                          {format(new Date(doc.document_date), 'dd.MM.yyyy')}
                        </span>
                      </div>
                    )}
                    <div className="flex items-center gap-3 px-3 py-2.5">
                      <Calendar className="w-4 h-4 text-gray-400 shrink-0" />
                      <span className="text-xs text-gray-500 w-28 shrink-0">Загружен</span>
                      <span className="text-sm font-medium text-gray-900 flex-1 text-right">
                        {format(new Date(doc.created_at), 'dd.MM.yyyy HH:mm')}
                      </span>
                    </div>
                    {doc.patient_name && (
                      <div className="flex items-center gap-3 px-3 py-2.5">
                        <User className="w-4 h-4 text-gray-400 shrink-0" />
                        <span className="text-xs text-gray-500 w-28 shrink-0">Пациент</span>
                        <span className="text-sm font-medium text-gray-900 flex-1 text-right truncate">
                          {doc.patient_name}
                        </span>
                      </div>
                    )}
                    {doc.medical_facility && (
                      <div className="flex items-center gap-3 px-3 py-2.5">
                        <Building2 className="w-4 h-4 text-gray-400 shrink-0" />
                        <span className="text-xs text-gray-500 w-28 shrink-0">Учреждение</span>
                        <span className="text-sm font-medium text-gray-900 flex-1 text-right truncate">
                          {doc.medical_facility}
                        </span>
                      </div>
                    )}
                    {doc.specialty && (
                      <div className="flex items-center gap-3 px-3 py-2.5">
                        <Stethoscope className="w-4 h-4 text-gray-400 shrink-0" />
                        <span className="text-xs text-gray-500 w-28 shrink-0">Специализация</span>
                        <span className="text-sm font-medium text-gray-900 flex-1 text-right truncate">
                          {doc.specialty}
                        </span>
                      </div>
                    )}
                    <div className="flex items-center gap-3 px-3 py-2.5">
                      <FileText className="w-4 h-4 text-gray-400 shrink-0" />
                      <span className="text-xs text-gray-500 w-28 shrink-0">Статус</span>
                      <span className={`text-sm font-medium flex-1 text-right ${statusLabel(doc.processing_status).color}`}>
                        {statusLabel(doc.processing_status).text}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 px-3 py-2.5">
                      <FileText className="w-4 h-4 text-gray-400 shrink-0" />
                      <span className="text-xs text-gray-500 w-28 shrink-0">Размер</span>
                      <span className="text-sm font-medium text-gray-900 flex-1 text-right">
                        {(doc.file_size / 1024 / 1024).toFixed(2)} МБ
                      </span>
                    </div>
                  </div>

                  {/* Summary */}
                  {doc.summary && (
                    <div>
                      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                        📝 AI-анализ
                      </h4>
                      <div className="bg-emerald-50 rounded-xl p-3 sm:p-4">
                        <p className={`text-sm text-gray-800 leading-relaxed whitespace-pre-wrap ${!summaryExpanded ? 'line-clamp-4' : ''}`}>
                          {doc.summary}
                        </p>
                        {doc.summary.length > 200 && (
                          <button
                            onClick={() => setSummaryExpanded(v => !v)}
                            className="mt-2 text-xs font-medium text-emerald-600"
                          >
                            {summaryExpanded ? 'Свернуть' : 'Читать полностью →'}
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Labs tab */}
              {isLabResult && activeTab === 'labs' && (
                <div className="p-3 sm:p-6">
                  <LabResultsTable documentId={doc.id} documentType={doc.document_type} />
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12">
              <p className="text-gray-500">Документ не найден</p>
            </div>
          )}
        </div>

        {/* Footer */}
        {doc && (
          <div
            className="px-4 py-3 border-t border-gray-100 bg-white flex items-center gap-2 shrink-0"
            style={{ paddingBottom: 'max(12px, env(safe-area-inset-bottom))' }}
          >
            <button
              onClick={handleOpenFile}
              className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2.5 bg-emerald-500 text-white rounded-xl font-medium text-sm"
            >
              <Eye className="h-4 w-4" />
              Открыть
            </button>
            <button
              onClick={handleDownload}
              className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2.5 bg-white border border-gray-200 text-gray-700 rounded-xl font-medium text-sm"
            >
              <Download className="h-4 w-4" />
              Скачать
            </button>
            <button
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="inline-flex items-center justify-center p-2.5 bg-red-50 text-red-500 rounded-xl disabled:opacity-50"
              title="Удалить"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
