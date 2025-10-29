import { useEffect, useState } from 'react'
import { documentsService } from '../../services/documents'
import { toast } from 'sonner'

interface LabResult {
  test_name: string
  value: string
  unit?: string | null
  reference_range?: string | null
  flag?: string | null
}

interface LabResultsTableProps {
  documentId: string
  documentType?: string | null
}

export default function LabResultsTable({ documentId, documentType }: LabResultsTableProps) {
  const [labResults, setLabResults] = useState<LabResult[]>([])
  const [loading, setLoading] = useState(false)
  const [hasLabs, setHasLabs] = useState<boolean | null>(null)

  useEffect(() => {
    // Only load for lab result documents
    if (documentType !== 'Результаты анализа') {
      return
    }

    const loadLabResults = async () => {
      setLoading(true)
      try {
        // First check if labs exist
        const summary = await documentsService.getLabsSummary(documentId)
        setHasLabs(summary.has_labs)
        
        if (summary.has_labs) {
          // Load full lab results
          const data = await documentsService.getLabs(documentId)
          setLabResults(data.lab_results)
        }
      } catch (error) {
        console.error('Error loading lab results:', error)
        toast.error('Не удалось загрузить результаты анализов')
      } finally {
        setLoading(false)
      }
    }

    loadLabResults()
  }, [documentId, documentType])

  // Don't render for non-lab documents
  if (documentType !== 'Результаты анализа') {
    return null
  }

  return (
    <div className="space-y-4">
      {loading ? (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-500">Загрузка анализов...</p>
        </div>
      ) : hasLabs === false ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-yellow-800">
            ⚠️ Для этого документа не извлечены результаты анализов
          </p>
        </div>
      ) : labResults.length > 0 ? (
        <div className="bg-gray-50 rounded-lg p-4 overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Аналит
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Значение
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Ед.
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Референс
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Флаг
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {labResults.map((result, idx) => (
                <tr key={idx} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">
                    {result.test_name}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 font-semibold">
                    {result.value}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {result.unit || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {result.reference_range || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        result.flag === 'H'
                          ? 'bg-red-100 text-red-800'
                          : result.flag === 'L'
                          ? 'bg-yellow-100 text-yellow-800'
                          : result.flag === 'A'
                          ? 'bg-purple-100 text-purple-800'
                          : 'bg-green-100 text-green-800'
                      }`}
                    >
                      {result.flag || 'N'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Legend */}
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-xs font-medium text-gray-700 mb-2">Обозначения флагов:</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  N
                </span>
                <span className="text-xs text-gray-600">Норма</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                  H
                </span>
                <span className="text-xs text-gray-600">Выше нормы</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                  L
                </span>
                <span className="text-xs text-gray-600">Ниже нормы</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                  A
                </span>
                <span className="text-xs text-gray-600">Аномальное</span>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

