import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { documentsService } from '../../services/documents'
import LineChart from './LineChart'
import DocumentModal from '../Documents/DocumentModal'

interface LabTrendModalProps {
  analyte: string | null
  onClose: () => void
}

export default function LabTrendModal({ analyte, onClose }: LabTrendModalProps) {
  const [excludedPoints, setExcludedPoints] = useState<Set<string>>(new Set())
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null)

  const { data: seriesData, isLoading } = useQuery({
    queryKey: ['labs_series', analyte],
    queryFn: () => documentsService.getLabTimeSeries(analyte!),
    enabled: !!analyte,
  })

  useEffect(() => {
    setExcludedPoints(new Set())
  }, [analyte])

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose])

  if (!analyte) return null

  const rawPoints = seriesData?.points || []
  const points = rawPoints.map((p, index) => ({
    ...p,
    _id: `${p.document_id || 'unknown'}_${p.date || 'nodate'}_${p.value_num}_${index}`,
  }))

  const togglePoint = (pointId: string) => {
    setExcludedPoints(prev => {
      const newSet = new Set(prev)
      if (newSet.has(pointId)) newSet.delete(pointId)
      else newSet.add(pointId)
      return newSet
    })
  }

  return (
    <>
      <div
        className="fixed inset-0 z-[120] flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm sm:p-4"
        style={{ display: selectedDocumentId ? 'none' : undefined }}
        onClick={onClose}
      >
        <div
          className="bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl max-w-5xl w-full overflow-hidden max-h-[92vh] flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-gray-100 flex items-center gap-3 shrink-0">
            <div className="w-9 h-9 rounded-xl bg-blue-50 flex items-center justify-center shrink-0">
              <span className="text-base">📊</span>
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm sm:text-base font-semibold text-gray-900 truncate">
                Динамика: {analyte}
              </h3>
              <div className="flex flex-wrap items-center gap-2 mt-0.5">
                {seriesData?.standard_unit && (
                  <span className="text-xs text-gray-500">
                    Единица: <span className="font-medium text-gray-700">{seriesData.standard_unit}</span>
                  </span>
                )}
                {seriesData?.category && (
                  <span className="text-xs text-gray-500">
                    · {seriesData.category}
                  </span>
                )}
              </div>
            </div>
            <button onClick={onClose} className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 shrink-0">
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6">
            {isLoading ? (
              <div className="flex items-center justify-center py-12 sm:py-16">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-10 w-10 sm:h-12 sm:w-12 border-b-2 border-[#4A90E2] mx-auto mb-3 sm:mb-4"></div>
                  <p className="text-xs sm:text-sm text-gray-600">Загрузка данных...</p>
                </div>
              </div>
            ) : points.length > 0 ? (
              <div className="bg-gradient-to-br from-gray-50 to-white p-3 sm:p-6 rounded-lg sm:rounded-xl border border-gray-100">
                <LineChart
                  points={points}
                  excludedPoints={excludedPoints}
                  onTogglePoint={togglePoint}
                  onOpenDocument={setSelectedDocumentId}
                  standardUnit={seriesData?.standard_unit || null}
                  referenceMin={seriesData?.reference_min ?? null}
                  referenceMax={seriesData?.reference_max ?? null}
                />
              </div>
            ) : (
              <div className="text-center py-12">
                <div className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4 rounded-full bg-gray-100 flex items-center justify-center">
                  <span className="text-2xl sm:text-3xl">📈</span>
                </div>
                <p className="text-xs sm:text-sm text-gray-500">Нет данных для отображения</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <DocumentModal
        documentId={selectedDocumentId}
        onClose={() => setSelectedDocumentId(null)}
      />
    </>
  )
}
