import { FileText, Download, Trash2, FlaskConical, AlertTriangle, CheckCircle2, CalendarOff } from 'lucide-react'
import { format } from 'date-fns'
import type { DocumentOrdersSummary } from '../../types'

interface LabsSummaryEntry {
  has_labs: boolean
  count: number
}

interface DocumentListItemProps {
  doc: {
    id: string
    original_filename: string
    document_type?: string | null
    document_subtype?: string | null
    document_date?: string | null
    specialty?: string | null
    research_area?: string | null
    orders_summary?: DocumentOrdersSummary | null
  }
  labsSummary?: Record<string, LabsSummaryEntry>
  showTags?: boolean
  onClick?: (id: string) => void
  onOpenLabs?: (id: string) => void
  onDownload?: (id: string, filename: string) => void
  onDelete?: (id: string) => void
}

export default function DocumentListItem({
  doc,
  labsSummary,
  showTags,
  onClick,
  onOpenLabs,
  onDownload,
  onDelete,
}: DocumentListItemProps) {
  return (
    <div
      className="flex items-center gap-3 px-3 sm:px-4 py-3 hover:bg-gray-50 active:bg-gray-100 transition-colors cursor-pointer"
      onClick={() => onClick?.(doc.id)}
    >
      {/* Icon */}
      <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center flex-shrink-0">
        <FileText className="h-5 w-5 text-emerald-500" />
      </div>

      {/* Main content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 min-w-0 flex-wrap">
          <p className="text-[14px] font-medium text-gray-900 truncate">
            {doc.original_filename}
          </p>
          {showTags && doc.document_subtype && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-100 flex-shrink-0">
              {doc.document_subtype}
            </span>
          )}
          {showTags && doc.specialty && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-sky-50 text-sky-700 border border-sky-100 flex-shrink-0">
              {doc.specialty}
            </span>
          )}
          {showTags && doc.research_area && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-100 flex-shrink-0">
              {doc.research_area}
            </span>
          )}
        </div>
        <p className="text-[12px] text-gray-400 truncate mt-0.5">
          {doc.document_type || '—'}
          {doc.document_date && ` · ${format(new Date(doc.document_date), 'dd.MM.yy')}`}
        </p>
        {!doc.document_date && (
          <span
            className="mt-1 inline-flex max-w-full items-center gap-1.5 rounded-md border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700"
            title="У документа нет даты — добавьте её в карточке, чтобы назначения закрывались корректно"
          >
            <CalendarOff className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">Добавьте дату</span>
          </span>
        )}
        {!!doc.orders_summary?.total && (
          <div
            className={`mt-1 inline-flex max-w-full items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-medium ${
              doc.orders_summary.pending > 0
                ? 'border-amber-200 bg-amber-50 text-amber-700'
                : 'border-emerald-200 bg-emerald-50 text-emerald-700'
            }`}
            title={
              doc.orders_summary.pending > 0
                ? `Невыполнено назначений: ${doc.orders_summary.pending}`
                : 'Нет активных напоминаний по назначениям'
            }
          >
            {doc.orders_summary.pending > 0 ? (
              <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
            ) : (
              <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
            )}
            <span className="truncate">
              {doc.orders_summary.pending > 0
                ? `Активные назначения: ${doc.orders_summary.pending}`
                : 'Назначения закрыты'}
            </span>
          </div>
        )}
      </div>

      {/* Actions */}
      {(onDownload || onDelete || onOpenLabs) && (
        <div className="flex items-center gap-0.5 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
          {doc.document_type === 'Результаты анализа' && labsSummary?.[doc.id]?.has_labs && (
            <button
              onClick={() => onOpenLabs?.(doc.id)}
              className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg text-purple-500 hover:bg-purple-50 transition-colors"
              title="Анализы"
            >
              <FlaskConical className="h-4 w-4" />
            </button>
          )}

          {onDownload && (
            <button
              onClick={() => onDownload(doc.id, doc.original_filename)}
              className="hidden sm:block p-1.5 rounded-lg text-gray-400 hover:text-emerald-500 hover:bg-emerald-50 transition-colors"
              title="Скачать"
            >
              <Download className="h-4 w-4" />
            </button>
          )}

          {onDelete && (
            <button
              onClick={() => onDelete(doc.id)}
              className="hidden sm:inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
              title="Удалить"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      )}
    </div>
  )
}
