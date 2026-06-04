import { useEffect, useState } from 'react'
import { X, Download, Trash2, FileText, Calendar, User, Building2, Stethoscope, FlaskConical, Eye, ClipboardList, CheckCircle2, AlertTriangle, ArrowLeft, MoreVertical } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { format } from 'date-fns'
import { documentsService } from '../../services/documents'
import type { DocumentOrderManualStatus } from '../../services/documents'
import type { DocumentExtractedTable } from '../../types'
import LabResultsTable from './LabResultsTable'

interface DocumentModalProps {
  documentId: string | null
  onClose: () => void
}

const ORDER_STATUS_OPTIONS: Array<{ value: DocumentOrderManualStatus; label: string }> = [
  { value: 'pending', label: 'Активно' },
  { value: 'completed', label: 'Выполнено без загрузки' },
  { value: 'not_required', label: 'Не требуется' },
  { value: 'incorrect', label: 'Ошибка распознавания' },
]

const orderStatusMeta = (status: DocumentOrderManualStatus) => ({
  pending: {
    text: 'Ожидает выполнения',
    detail: 'Будет показываться как напоминание',
    cardClass: 'border-amber-100 bg-amber-50',
    iconClass: 'text-amber-600',
    textClass: 'text-amber-700',
  },
  completed: {
    text: 'Выполнено',
    detail: 'Не будет показываться как напоминание',
    cardClass: 'border-emerald-100 bg-emerald-50',
    iconClass: 'text-emerald-600',
    textClass: 'text-emerald-700',
  },
  not_required: {
    text: 'Не требуется',
    detail: 'Исключено из активных напоминаний',
    cardClass: 'border-gray-200 bg-gray-50',
    iconClass: 'text-gray-500',
    textClass: 'text-gray-600',
  },
  incorrect: {
    text: 'Ошибка распознавания',
    detail: 'Исключено из активных напоминаний',
    cardClass: 'border-gray-200 bg-gray-50',
    iconClass: 'text-gray-500',
    textClass: 'text-gray-600',
  },
}[status])

const tableColumns = (table: DocumentExtractedTable) => {
  if (table.columns?.length) return table.columns
  const keys = new Set<string>()
  ;(table.rows || []).forEach((row) => {
    Object.keys(row || {}).forEach((key) => keys.add(key))
  })
  return Array.from(keys)
}

const formatCell = (value: unknown) => {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return JSON.stringify(value)
}

const fullTextSourceLabel = (source?: string | null) => ({
  pdf_text_extraction: 'PDF-текст',
  docx_text_extraction: 'DOCX-текст',
  ai_vision_transcription: 'AI-транскрипция',
}[source || ''] || source)

export default function DocumentModal({ documentId, onClose }: DocumentModalProps) {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'info' | 'labs'>('info')
  const [summaryExpanded, setSummaryExpanded] = useState(false)
  const [showFullContent, setShowFullContent] = useState(false)
  const [showActionsMenu, setShowActionsMenu] = useState(false)

  const { data: doc, isLoading } = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => documentsService.getDocument(documentId!),
    enabled: !!documentId,
  })

  const {
    data: documentContent,
    isLoading: isContentLoading,
    isError: isContentError,
  } = useQuery({
    queryKey: ['document-content', doc?.id],
    queryFn: () => documentsService.getDocumentContent(doc!.id),
    enabled: !!doc?.id && showFullContent,
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

  const orderStatusMutation = useMutation({
    mutationFn: ({
      documentId,
      orderIndex,
      status,
    }: {
      documentId: string
      orderIndex: number
      status: DocumentOrderManualStatus
    }) => documentsService.updateOrderStatus(documentId, orderIndex, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document', documentId] })
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      queryClient.invalidateQueries({ queryKey: ['documents-count'] })
      queryClient.invalidateQueries({ queryKey: ['documents-all'] })
      toast.success('Статус назначения обновлён')
    },
    onError: () => {
      toast.error('Не удалось обновить статус назначения')
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

  const handleOpenMatchedDocument = async (matchedDocumentId: string) => {
    const targetWindow = window.open('', '_blank')
    try {
      await documentsService.openDocument(matchedDocumentId, targetWindow)
    } catch {
      toast.error('Не удалось открыть документ')
    }
  }

  const handleOrderStatusChange = (orderIndex: number, status: DocumentOrderManualStatus) => {
    if (!doc) return
    orderStatusMutation.mutate({
      documentId: doc.id,
      orderIndex,
      status,
    })
  }

  const handleDelete = () => {
    if (!doc) return
    setShowActionsMenu(false)
    if (window.confirm('Вы уверены, что хотите удалить этот документ?')) {
      deleteMutation.mutate(doc.id)
    }
  }

  useEffect(() => {
    setSummaryExpanded(false)
    setShowFullContent(false)
    setShowActionsMenu(false)
  }, [documentId])

  useEffect(() => {
    if (doc) {
      setActiveTab(doc.document_type === 'Результаты анализа' ? 'labs' : 'info')
      setShowFullContent(false)
    }
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
          <button onClick={onClose} className="min-h-11 min-w-11 inline-flex items-center justify-center rounded-xl text-gray-400 shrink-0" aria-label="Закрыть">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tabs — only for lab results */}
        {isLabResult && !showFullContent && (
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
              {showFullContent && (
                <div className="p-4 sm:p-6 space-y-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0">
                      <button
                        type="button"
                        onClick={() => setShowFullContent(false)}
                        className="mb-2 inline-flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-gray-900"
                      >
                        <ArrowLeft className="h-4 w-4" />
                        AI-анализ
                      </button>
                      <h4 className="text-base font-semibold text-gray-900">Полное содержание</h4>
                    </div>
                    {documentContent?.full_text_source && (
                      <span className="self-start rounded-md border border-gray-200 bg-gray-50 px-2 py-1 text-xs font-medium text-gray-500 sm:self-auto">
                        {fullTextSourceLabel(documentContent.full_text_source)}
                      </span>
                    )}
                  </div>

                  {isContentLoading ? (
                    <div className="flex items-center justify-center py-12">
                      <div className="animate-spin rounded-full h-9 w-9 border-b-2 border-emerald-500" />
                    </div>
                  ) : isContentError ? (
                    <div className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">
                      Не удалось загрузить полное содержание документа.
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {documentContent?.full_text ? (
                        <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
                          <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-6 text-gray-800">
                            {documentContent.full_text}
                          </pre>
                        </div>
                      ) : (
                        <div className="rounded-xl border border-amber-100 bg-amber-50 p-4 text-sm text-amber-800">
                          Полное содержание для этого документа пока не извлечено.
                        </div>
                      )}

                      {!!documentContent?.tables?.length && (
                        <div className="space-y-3">
                          <h5 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                            Табличные данные
                          </h5>
                          {documentContent.tables.map((table, tableIndex) => {
                            const columns = tableColumns(table)
                            return (
                              <div key={`${table.title || 'table'}-${tableIndex}`} className="overflow-hidden rounded-xl border border-gray-100">
                                {table.title && (
                                  <div className="border-b border-gray-100 bg-gray-50 px-3 py-2 text-sm font-medium text-gray-800">
                                    {table.title}
                                  </div>
                                )}
                                <div className="overflow-x-auto">
                                  <table className="min-w-full divide-y divide-gray-100 text-sm">
                                    {!!columns.length && (
                                      <thead className="bg-gray-50">
                                        <tr>
                                          {columns.map((column) => (
                                            <th key={column} className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                                              {column}
                                            </th>
                                          ))}
                                        </tr>
                                      </thead>
                                    )}
                                    <tbody className="divide-y divide-gray-100 bg-white">
                                      {(table.rows || []).map((row, rowIndex) => (
                                        <tr key={rowIndex}>
                                          {columns.map((column) => (
                                            <td key={column} className="px-3 py-2 align-top text-gray-800">
                                              {formatCell(row?.[column])}
                                            </td>
                                          ))}
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      )}

                      {!!documentContent?.lab_results?.length && (
                        <div className="space-y-3">
                          <h5 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                            Извлеченные анализы
                          </h5>
                          <div className="overflow-hidden rounded-xl border border-gray-100">
                            <div className="overflow-x-auto">
                              <table className="min-w-full divide-y divide-gray-100 text-sm">
                                <thead className="bg-gray-50">
                                  <tr>
                                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Показатель</th>
                                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Значение</th>
                                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Ед.</th>
                                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Референс</th>
                                    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Флаг</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-100 bg-white">
                                  {documentContent.lab_results.map((result, resultIndex) => (
                                    <tr key={`${result.test_name || 'lab'}-${resultIndex}`}>
                                      <td className="px-3 py-2 align-top font-medium text-gray-900">{result.test_name || ''}</td>
                                      <td className="px-3 py-2 align-top text-gray-800">{result.value || ''}</td>
                                      <td className="px-3 py-2 align-top text-gray-600">{result.unit || ''}</td>
                                      <td className="px-3 py-2 align-top text-gray-600">{result.reference_range || ''}</td>
                                      <td className="px-3 py-2 align-top text-gray-600">{result.flag || ''}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Info tab */}
              {!showFullContent && (!isLabResult || activeTab === 'info') && (
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

                  {!!doc.orders_summary?.total && (
                    <div>
                      <div className="flex items-center justify-between gap-3 mb-2">
                        <h4 className="flex items-center gap-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                          <ClipboardList className="h-4 w-4" />
                          Назначения
                        </h4>
                        <span
                          className={`shrink-0 rounded-md border px-2 py-0.5 text-[11px] font-medium ${
                            doc.orders_summary.pending > 0
                              ? 'border-amber-200 bg-amber-50 text-amber-700'
                              : 'border-emerald-200 bg-emerald-50 text-emerald-700'
                          }`}
                        >
                          {doc.orders_summary.pending > 0
                            ? `Активно: ${doc.orders_summary.pending}`
                            : 'Нет активных'}
                        </span>
                      </div>
                      <div className="space-y-2">
                        {doc.orders_summary.items.map((order, index) => {
                          const meta = orderStatusMeta(order.status)
                          const isActive = order.status === 'pending'
                          const matchedDate = order.matched_document_date
                            ? format(new Date(order.matched_document_date), 'dd.MM.yyyy')
                            : null

                          return (
                            <div
                              key={`${order.title}-${index}`}
                              className={`rounded-xl border p-3 ${meta.cardClass}`}
                            >
                              <div className="flex items-start gap-2 sm:gap-3">
                                {isActive ? (
                                  <AlertTriangle className={`mt-0.5 h-4 w-4 shrink-0 ${meta.iconClass}`} />
                                ) : (
                                  <CheckCircle2 className={`mt-0.5 h-4 w-4 shrink-0 ${meta.iconClass}`} />
                                )}
                                <div className="min-w-0 flex-1">
                                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                                    <p className="text-sm font-medium text-gray-900">{order.title}</p>
                                    <select
                                      value={order.status}
                                      onChange={(e) => handleOrderStatusChange(order.order_index, e.target.value as DocumentOrderManualStatus)}
                                      disabled={orderStatusMutation.isPending}
                                      className="h-8 rounded-md border border-gray-200 bg-white px-2 text-xs font-medium text-gray-700 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100 disabled:opacity-60"
                                    >
                                      {ORDER_STATUS_OPTIONS.map((option) => (
                                        <option key={option.value} value={option.value}>
                                          {option.label}
                                        </option>
                                      ))}
                                    </select>
                                  </div>
                                  <p className="mt-0.5 text-xs text-gray-600">
                                    {order.target_document_type || 'Назначение'}
                                    {order.target_document_subtype && ` · ${order.target_document_subtype}`}
                                    {order.target_research_area && ` · ${order.target_research_area}`}
                                  </p>
                                  <p className={`mt-2 text-xs ${meta.textClass}`}>
                                    {meta.text}
                                    {order.status_source === 'manual' ? ' · вручную' : ' · автоматически'}
                                  </p>
                                  {order.status === 'completed' && order.matched_document_id ? (
                                    <div className="mt-2 flex flex-wrap items-center gap-2">
                                      {matchedDate && <span className="text-xs text-emerald-700">Найдено {matchedDate}</span>}
                                      {order.matched_document_id && (
                                        <button
                                          type="button"
                                          onClick={() => handleOpenMatchedDocument(order.matched_document_id!)}
                                          className="rounded-md bg-white px-2 py-1 text-xs font-medium text-emerald-700 border border-emerald-200"
                                        >
                                          Открыть результат
                                        </button>
                                      )}
                                    </div>
                                  ) : (
                                    <p className={`mt-1 text-xs ${meta.textClass}`}>{meta.detail}</p>
                                  )}
                                </div>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {/* Summary */}
                  {doc.summary && (
                    <div>
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                          📝 AI-анализ
                        </h4>
                        {doc.processing_status === 'completed' && (
                          <button
                            type="button"
                            onClick={() => setShowFullContent(true)}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-100 bg-white px-2.5 py-1.5 text-xs font-medium text-emerald-700 shadow-sm hover:bg-emerald-50"
                          >
                            <FileText className="h-3.5 w-3.5" />
                            Полное содержание
                          </button>
                        )}
                      </div>
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
              {!showFullContent && isLabResult && activeTab === 'labs' && (
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
            className="relative px-4 py-3 border-t border-gray-100 bg-white flex items-center gap-2 shrink-0"
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
              onClick={() => setShowActionsMenu((value) => !value)}
              className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-xl border border-gray-200 bg-white text-gray-500"
              aria-label="Дополнительные действия"
              aria-expanded={showActionsMenu}
            >
              <MoreVertical className="h-4 w-4" />
            </button>
            {showActionsMenu && (
              <div className="absolute bottom-full right-4 mb-2 w-52 overflow-hidden rounded-xl border border-gray-100 bg-white shadow-xl">
                <button
                  onClick={handleDelete}
                  disabled={deleteMutation.isPending}
                  className="flex min-h-11 w-full items-center gap-2 px-3 py-2.5 text-left text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
                >
                  <Trash2 className="h-4 w-4" />
                  Удалить документ
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
