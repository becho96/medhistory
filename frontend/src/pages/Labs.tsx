import { useEffect, useState, useMemo, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { documentsService } from '../services/documents'
import { Search, ChevronDown, ChevronRight, FlaskConical } from 'lucide-react'
import DocumentModal from '../components/Documents/DocumentModal'
import LineChart from '../components/Labs/LineChart'


function pluralMeasurements(count: number): string {
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod10 === 1 && mod100 !== 11) return 'измерение'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'измерения'
  return 'измерений'
}

const categoryIcons: Record<string, string> = {
  'Общий анализ крови': '🩸',
  'Биохимия крови': '🧪',
  'Липидный профиль': '💧',
  'Коагулограмма': '🩹',
  'Гормоны': '⚗️',
  'Витамины и микроэлементы': '💊',
  'Маркеры воспаления': '🔥',
  'Общий анализ мочи': '🚽',
  'Инфекции': '🦠',
  'Микробиология': '🔬',
  'Онкомаркеры': '🎯',
  'Аутоиммунные маркеры': '🛡️',
  'Другое': '📋'
}

interface AnalyteSelectorProps {
  categories: Array<{
    name: string
    analytes: Array<{
      canonical_name: string
      standard_unit: string | null
      count: number
    }>
  }>
  selectedAnalyte: string
  onSelect: (analyteName: string) => void
}

function AnalyteSelector({ categories, selectedAnalyte, onSelect }: AnalyteSelectorProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())

  const filteredCategories = useMemo(() => {
    if (!searchQuery.trim()) return categories
    const query = searchQuery.toLowerCase()
    return categories
      .map(category => ({ ...category, analytes: category.analytes.filter(a => a.canonical_name.toLowerCase().includes(query)) }))
      .filter(category => category.analytes.length > 0)
  }, [categories, searchQuery])

  useEffect(() => {
    if (searchQuery.trim()) {
      setExpandedCategories(new Set(filteredCategories.map(c => c.name)))
    }
  }, [searchQuery, filteredCategories])

  const toggleCategory = (categoryName: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev)
      if (newSet.has(categoryName)) newSet.delete(categoryName)
      else newSet.add(categoryName)
      return newSet
    })
  }

  const totalAnalytes = categories.reduce((sum, c) => sum + c.analytes.length, 0)

  return (
    <div className="space-y-3">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          type="text"
          placeholder={`Поиск среди ${totalAnalytes} анализов...`}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#4A90E2] focus:border-[#4A90E2] bg-white"
        />
        {searchQuery && (
          <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
            ×
          </button>
        )}
      </div>

      <div className="max-h-[400px] overflow-y-auto border border-gray-200 rounded-lg bg-white">
        {filteredCategories.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-500">Анализы не найдены</div>
        ) : (
          filteredCategories.map((category) => (
            <div key={category.name} className="border-b border-gray-100 last:border-b-0">
              <button
                onClick={() => toggleCategory(category.name)}
                className="w-full flex min-h-12 items-center justify-between px-3 py-2.5 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">{categoryIcons[category.name] || '📋'}</span>
                  <span className="text-sm font-medium text-gray-900">{category.name}</span>
                  <span className="text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">{category.analytes.length}</span>
                </div>
                {expandedCategories.has(category.name)
                  ? <ChevronDown className="h-4 w-4 text-gray-400" />
                  : <ChevronRight className="h-4 w-4 text-gray-400" />
                }
              </button>
              {expandedCategories.has(category.name) && (
                <div className="bg-gray-50/50 border-t border-gray-100">
                  {category.analytes.map((analyte) => (
                    <button
                      key={analyte.canonical_name}
                      onClick={() => onSelect(analyte.canonical_name)}
                      className={`w-full flex min-h-11 items-center justify-between gap-3 px-4 py-2.5 text-left hover:bg-gray-100 transition-colors ${
                        selectedAnalyte === analyte.canonical_name
                          ? 'bg-blue-50 border-l-2 border-l-blue-500'
                          : 'border-l-2 border-l-transparent'
                      }`}
                    >
                      <div className="flex min-w-0 flex-col sm:flex-row sm:items-center sm:gap-2">
                        <span className={`text-sm ${selectedAnalyte === analyte.canonical_name ? 'font-medium text-blue-900' : 'text-gray-700'}`}>
                          {analyte.canonical_name}
                        </span>
                        {analyte.standard_unit && (
                          <span className="mt-0.5 text-xs text-gray-500 sm:mt-0">({analyte.standard_unit})</span>
                        )}
                      </div>
                      <span className="shrink-0 text-xs text-gray-400">{analyte.count} изм.</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default function Labs() {
  const [selected, setSelected] = useState<string>('')
  const [excludedPoints, setExcludedPoints] = useState<Set<string>>(new Set())
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null)
  const chartSectionRef = useRef<HTMLDivElement>(null)

  const { data: analytesData, isLoading: loadingAnalytes } = useQuery({
    queryKey: ['labs_analytes'],
    queryFn: () => documentsService.listAnalytes(),
  })

  const categories = analytesData?.categories || []

  const { data: seriesData, isLoading: loadingSeries } = useQuery({
    queryKey: ['labs_series', selected],
    queryFn: () => documentsService.getLabTimeSeries(selected),
    enabled: !!selected,
  })

  const rawPoints = (seriesData?.points || []) as Array<{
    date?: string
    value_num: number
    unit?: string | null
    document_id?: string
    reference_range?: string | null
    flag?: string | null
  }>

  const points = rawPoints.map((p, index) => ({
    ...p,
    _id: `${p.document_id || 'unknown'}_${p.date || 'nodate'}_${p.value_num}_${index}`,
  }))

  // Измерения, которые не удалось привести к стандартной единице: без пояснения
  // график выглядит пустым, хотя в списке анализов у показателя есть измерения.
  const skipped = seriesData?.skipped || []

  useEffect(() => {
    setExcludedPoints(new Set())
  }, [selected])

  const togglePoint = (pointId: string) => {
    setExcludedPoints(prev => {
      const newSet = new Set(prev)
      if (newSet.has(pointId)) newSet.delete(pointId)
      else newSet.add(pointId)
      return newSet
    })
  }

  const handleSelectAnalyte = (analyteName: string) => {
    setSelected(analyteName)
    window.setTimeout(() => {
      chartSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 120)
  }

  return (
    <div className="space-y-4 md:space-y-8 page-transition">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 sm:gap-3 mb-2 sm:mb-3">
          <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg sm:rounded-xl bg-gradient-to-br from-red-100 to-pink-50 flex items-center justify-center shadow-lg shadow-red-200/50">
            <FlaskConical className="h-5 w-5 sm:h-6 sm:w-6 text-red-600" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-900">Анализы</h1>
          </div>
        </div>
        <p className="text-sm sm:text-base md:text-lg text-gray-600 mt-1 sm:mt-2">
          Выберите анализ и посмотрите динамику показателей
        </p>
      </div>

      {/* Analyte selector */}
      <div className="medical-card">
        <div className="flex items-center gap-2 min-w-0 mb-3">
          <span className="text-lg shrink-0">🧪</span>
          <h3 className="text-sm sm:text-base font-semibold text-gray-900 truncate">
            Выберите анализ
          </h3>
        </div>

        <div>
          {loadingAnalytes ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#4A90E2]"></div>
            </div>
          ) : categories.length > 0 ? (
            <AnalyteSelector
              categories={categories}
              selectedAnalyte={selected}
              onSelect={handleSelectAnalyte}
            />
          ) : (
            <div className="text-center py-8 text-sm text-gray-500">Нет доступных анализов</div>
          )}

          {selected && seriesData && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">Выбран:</span>
                  <span className="text-sm font-medium text-gray-900">{selected}</span>
                </div>
                {seriesData.standard_unit && (
                  <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-50 rounded-md">
                    <span className="text-xs text-blue-600">Единица измерения:</span>
                    <span className="text-xs font-medium text-blue-700">{seriesData.standard_unit}</span>
                  </div>
                )}
                {seriesData.category && (
                  <div className="flex items-center gap-1.5 px-2 py-1 bg-purple-50 rounded-md">
                    <span className="text-xs text-purple-600">Категория:</span>
                    <span className="text-xs font-medium text-purple-700">{seriesData.category}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Chart */}
      <div ref={chartSectionRef} className="medical-card scroll-mt-20">
        <div className="flex items-center gap-2 mb-4 sm:mb-6">
          <h3 className="text-base sm:text-xl font-semibold text-gray-900">📊 График динамики</h3>
        </div>
        {loadingSeries ? (
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
              referenceMin={seriesData?.reference_min || null}
              referenceMax={seriesData?.reference_max || null}
            />
            {skipped.length > 0 && (
              <p className="mt-3 text-xs text-gray-500">
                Не показано на графике: {skipped.map(s => `${s.count} ${pluralMeasurements(s.count)} в единицах «${s.unit}»`).join(', ')}
              </p>
            )}
          </div>
        ) : (
          <div className="text-center py-12">
            <div className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4 rounded-full bg-gray-100 flex items-center justify-center">
              <span className="text-2xl sm:text-3xl">📈</span>
            </div>
            <p className="text-xs sm:text-sm text-gray-500">
              {selected ? 'Нет данных для отображения' : 'Выберите анализ для просмотра'}
            </p>
            {skipped.length > 0 && (
              <p className="mt-2 text-xs text-gray-400">
                {skipped.map(s => `${s.count} ${pluralMeasurements(s.count)} в единицах «${s.unit}»`).join(', ')}
                {seriesData?.standard_unit ? ` не приведены к «${seriesData.standard_unit}»` : ' не удалось распознать'}
              </p>
            )}
          </div>
        )}
      </div>

      <DocumentModal
        documentId={selectedDocumentId}
        onClose={() => setSelectedDocumentId(null)}
      />
    </div>
  )
}
