import { useEffect, useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { documentsService } from '../services/documents'
import { Search, ChevronDown, ChevronRight, FlaskConical, FileText } from 'lucide-react'
import DocumentModal from '../components/Documents/DocumentModal'

interface ChartPoint {
  date?: string
  value_num: number
  value_str?: string
  unit?: string | null
  document_id?: string
  reference_range?: string | null
  flag?: string | null
  _id?: string
}

interface LineChartProps {
  points: Array<ChartPoint>
  excludedPoints: Set<string>
  onTogglePoint: (pointId: string) => void
  onOpenDocument: (documentId: string) => void
  standardUnit: string | null
  referenceMin: number | null
  referenceMax: number | null
}

function LineChart({ points, excludedPoints, onTogglePoint, onOpenDocument, standardUnit, referenceMin, referenceMax }: LineChartProps) {
  const [hoveredPoint, setHoveredPoint] = useState<number | null>(null)
  const width = 1000
  const height = 400
  const padding = { top: 40, right: 40, bottom: 70, left: 80 }

  const data = points
    .filter((p) => typeof p.value_num === 'number' && p.date && !excludedPoints.has(p._id || ''))
    .sort((a, b) => new Date(a.date || '').getTime() - new Date(b.date || '').getTime())

  if (data.length === 0) {
    return <div className="text-sm text-gray-500">Нет данных для отображения</div>
  }

  const values = data.map((p) => p.value_num)
  const minValue = Math.min(...values)
  const maxValue = Math.max(...values)
  const avgValue = values.reduce((a, b) => a + b, 0) / values.length

  const getValueStatus = (value: number): 'normal' | 'warning' | 'danger' => {
    if (!referenceMin || !referenceMax) return 'normal'
    const range = referenceMax - referenceMin
    const warningThreshold = range * 0.1
    if (value >= referenceMin && value <= referenceMax) return 'normal'
    if (
      (value < referenceMin && value >= referenceMin - warningThreshold) ||
      (value > referenceMax && value <= referenceMax + warningThreshold)
    ) return 'warning'
    return 'danger'
  }

  const statusColors = { normal: '#10b981', warning: '#f59e0b', danger: '#ef4444' }

  // Latest value for hero display
  const sortedDesc = [...data].sort((a, b) => new Date(b.date!).getTime() - new Date(a.date!).getTime())
  const latestPoint = sortedDesc[0]
  const prevPoint = sortedDesc[1]
  const latestStatus = latestPoint ? getValueStatus(latestPoint.value_num) : 'normal'
  const trend = latestPoint && prevPoint
    ? (latestPoint.value_num > prevPoint.value_num ? 'up' : latestPoint.value_num < prevPoint.value_num ? 'down' : 'stable')
    : null

  const statusStyles = {
    normal: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', badge: 'bg-emerald-100 text-emerald-700', label: 'В норме' },
    warning: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', badge: 'bg-amber-100 text-amber-700', label: 'Близко к границе' },
    danger: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', badge: 'bg-red-100 text-red-700', label: 'Вне нормы' },
  }
  const currentStyle = statusStyles[latestStatus]

  const dates = data.map((p) => new Date(p.date!).getTime())
  const minX = Math.min(...dates)
  const maxX = Math.max(...dates)

  const allYValues = [...values]
  if (referenceMin !== null) allYValues.push(referenceMin)
  if (referenceMax !== null) allYValues.push(referenceMax)

  const dataMinY = Math.min(...allYValues)
  const dataMaxY = Math.max(...allYValues)
  const yPadding = (dataMaxY - dataMinY) * 0.15 || 1
  const minY = dataMinY - yPadding
  const maxY = dataMaxY + yPadding

  const chartWidth = width - padding.left - padding.right
  const chartHeight = height - padding.top - padding.bottom

  const xScale = (t: number) => {
    if (maxX === minX) return padding.left + chartWidth / 2
    return padding.left + ((t - minX) / (maxX - minX)) * chartWidth
  }

  const yScale = (v: number) => {
    if (maxY === minY) return padding.top + chartHeight / 2
    return padding.top + chartHeight - ((v - minY) / (maxY - minY)) * chartHeight
  }

  const linePath = data
    .map((p, i) => {
      const x = xScale(new Date(p.date!).getTime())
      const y = yScale(p.value_num)
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`
    })
    .join(' ')

  const yGridLines = 6
  const xGridLines = Math.min(data.length, 8)
  const yTicks = Array.from({ length: yGridLines }, (_, i) => minY + ((maxY - minY) * i) / (yGridLines - 1))
  const xTicks = Array.from({ length: xGridLines }, (_, i) => minX + ((maxX - minX) * i) / (xGridLines - 1))

  const formatDate = (t: number) => {
    const date = new Date(t)
    return date.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' })
  }

  const formatValue = (v: number) => (v % 1 === 0 ? v.toString() : v.toFixed(2))

  const displayUnit = standardUnit || data[0]?.unit || ''

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Latest value hero + min/max */}
      <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
        {latestPoint && (
          <div className={`flex-1 rounded-xl p-3 sm:p-4 border ${currentStyle.border} ${currentStyle.bg}`}>
            <div className="flex items-start justify-between gap-2 mb-1">
              <p className="text-xs font-medium text-gray-500">Последнее измерение</p>
              <span className={`text-[10px] sm:text-xs font-semibold px-1.5 py-0.5 rounded-full ${currentStyle.badge}`}>
                {currentStyle.label}
              </span>
            </div>
            <div className={`text-2xl sm:text-3xl font-bold ${currentStyle.text}`}>
              {formatValue(latestPoint.value_num)}
              <span className="text-base font-medium ml-1 opacity-70">{displayUnit}</span>
              {trend && (
                <span className="text-sm ml-1 opacity-80">
                  {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}
                </span>
              )}
            </div>
            <p className="text-xs text-gray-400 mt-0.5">{formatDate(new Date(latestPoint.date!).getTime())}</p>
            {referenceMin !== null && referenceMax !== null && (
              <p className="text-xs text-gray-500 mt-1.5 pt-1.5 border-t border-black/5">
                Норма: {formatValue(referenceMin)} — {formatValue(referenceMax)} {displayUnit}
              </p>
            )}
          </div>
        )}
        <div className="flex sm:flex-col gap-2">
          <div className="flex-1 bg-gradient-to-br from-blue-50 to-blue-100/50 rounded-xl p-2 sm:p-3 border border-blue-200 min-w-[80px]">
            <div className="text-xs font-medium text-blue-600 mb-0.5">Минимум</div>
            <div className="text-base sm:text-xl font-bold text-blue-900">{formatValue(minValue)}</div>
            <div className="text-xs text-blue-600">{displayUnit}</div>
          </div>
          <div className="flex-1 bg-gradient-to-br from-purple-50 to-purple-100/50 rounded-xl p-2 sm:p-3 border border-purple-200 min-w-[80px]">
            <div className="text-xs font-medium text-purple-600 mb-0.5">Максимум</div>
            <div className="text-base sm:text-xl font-bold text-purple-900">{formatValue(maxValue)}</div>
            <div className="text-xs text-purple-600">{displayUnit}</div>
          </div>
        </div>
      </div>

      {/* Chart and Legend */}
      <div className="flex flex-col md:flex-row gap-4 md:gap-6 items-start">
        <div className="relative flex-1 min-w-0 w-full">
          <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="w-full h-auto" style={{ maxWidth: '100%' }}>
            <defs>
              <linearGradient id="normalZoneGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10b981" stopOpacity="0.12" />
                <stop offset="100%" stopColor="#10b981" stopOpacity="0.12" />
              </linearGradient>
              <linearGradient id="lineGradient" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#8b5cf6" />
                <stop offset="50%" stopColor="#6366f1" />
                <stop offset="100%" stopColor="#3b82f6" />
              </linearGradient>
              <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur in="SourceAlpha" stdDeviation="3"/>
                <feOffset dx="0" dy="2" result="offsetblur"/>
                <feComponentTransfer>
                  <feFuncA type="linear" slope="0.2"/>
                </feComponentTransfer>
                <feMerge>
                  <feMergeNode/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>

            {/* Grid lines */}
            <g opacity="0.4">
              {yTicks.map((v, i) => (
                <line key={`y-grid-${i}`} x1={padding.left} y1={yScale(v)} x2={width - padding.right} y2={yScale(v)} stroke="#e5e7eb" strokeWidth="1" strokeDasharray="4,4" />
              ))}
              {xTicks.map((t, i) => (
                <line key={`x-grid-${i}`} x1={xScale(t)} y1={padding.top} x2={xScale(t)} y2={height - padding.bottom} stroke="#e5e7eb" strokeWidth="1" strokeDasharray="4,4" />
              ))}
            </g>

            {referenceMin !== null && referenceMax !== null && (
              <rect x={padding.left} y={yScale(referenceMax)} width={chartWidth} height={yScale(referenceMin) - yScale(referenceMax)} fill="url(#normalZoneGradient)" />
            )}

            {referenceMin !== null && (
              <>
                <line x1={padding.left} y1={yScale(referenceMin)} x2={width - padding.right} y2={yScale(referenceMin)} stroke="#ef4444" strokeWidth="2" strokeDasharray="6,3" opacity="0.6" />
                <text x={width - padding.right - 5} y={yScale(referenceMin) - 8} textAnchor="end" fontSize="11" fill="#ef4444" fontWeight="600">
                  Мин: {formatValue(referenceMin)} {displayUnit}
                </text>
              </>
            )}

            {referenceMax !== null && (
              <>
                <line x1={padding.left} y1={yScale(referenceMax)} x2={width - padding.right} y2={yScale(referenceMax)} stroke="#ef4444" strokeWidth="2" strokeDasharray="6,3" opacity="0.6" />
                <text x={width - padding.right - 5} y={yScale(referenceMax) - 8} textAnchor="end" fontSize="11" fill="#ef4444" fontWeight="600">
                  Макс: {formatValue(referenceMax)} {displayUnit}
                </text>
              </>
            )}

            <path d={linePath} fill="none" stroke="url(#lineGradient)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" filter="url(#shadow)">
              <animate attributeName="stroke-dasharray" from="0, 1000" to="1000, 0" dur="1.5s" fill="freeze" />
            </path>

            {data.map((p, i) => {
              const x = xScale(new Date(p.date!).getTime())
              const y = yScale(p.value_num)
              const isHovered = hoveredPoint === i
              const status = getValueStatus(p.value_num)
              const pointColor = statusColors[status]

              return (
                <g key={i}>
                  {isHovered && (
                    <circle cx={x} cy={y} r="12" fill={pointColor} opacity="0.2">
                      <animate attributeName="r" values="12;16;12" dur="1.5s" repeatCount="indefinite" />
                    </circle>
                  )}
                  <circle
                    cx={x} cy={y}
                    r={isHovered ? "6" : "4"}
                    fill={isHovered ? pointColor : "#ffffff"}
                    stroke={pointColor}
                    strokeWidth={isHovered ? "3" : "2"}
                    style={{ cursor: p.document_id ? 'pointer' : 'default', transition: 'all 0.2s ease' }}
                    onMouseEnter={() => setHoveredPoint(i)}
                    onMouseLeave={() => setHoveredPoint(null)}
                    onClick={() => p.document_id && onOpenDocument(p.document_id)}
                    filter={isHovered ? "url(#shadow)" : undefined}
                  />
                  {isHovered && (
                    <g>
                      <rect x={x - 85} y={y - 80} width="170" height={p.document_id ? 70 : 55} fill="#1f2937" rx="8" opacity="0.95" filter="url(#shadow)" />
                      <text x={x} y={y - 57} textAnchor="middle" fontSize="12" fill="#ffffff" fontWeight="600">
                        {formatDate(new Date(p.date!).getTime())}
                      </text>
                      <text x={x} y={y - 40} textAnchor="middle" fontSize="16" fill={pointColor} fontWeight="bold">
                        {formatValue(p.value_num)} {displayUnit}
                      </text>
                      {p.document_id && (
                        <text x={x} y={y - 20} textAnchor="middle" fontSize="10" fill="#93c5fd">
                          ↗ Открыть документ
                        </text>
                      )}
                    </g>
                  )}
                </g>
              )
            })}

            <line x1={padding.left} y1={padding.top} x2={padding.left} y2={height - padding.bottom} stroke="#9ca3af" strokeWidth="2" />
            <line x1={padding.left} y1={height - padding.bottom} x2={width - padding.right} y2={height - padding.bottom} stroke="#9ca3af" strokeWidth="2" />

            {yTicks.map((v, i) => (
              <text key={`y-label-${i}`} x={padding.left - 12} y={yScale(v) + 4} textAnchor="end" fontSize="12" fill="#6b7280" fontWeight="500">
                {formatValue(v)}
              </text>
            ))}

            {xTicks.map((t, i) => (
              <g key={`x-label-${i}`}>
                <text x={xScale(t)} y={height - padding.bottom + 20} textAnchor="middle" fontSize="11" fill="#6b7280" fontWeight="500">
                  {formatDate(t).split(' ')[0]}
                </text>
                <text x={xScale(t)} y={height - padding.bottom + 35} textAnchor="middle" fontSize="10" fill="#9ca3af">
                  {formatDate(t).split(' ').slice(1).join(' ')}
                </text>
              </g>
            ))}

            <text x={padding.left - 60} y={padding.top + chartHeight / 2} textAnchor="middle" fontSize="13" fill="#4b5563" fontWeight="600" transform={`rotate(-90 ${padding.left - 60} ${padding.top + chartHeight / 2})`}>
              {displayUnit || 'Значение'}
            </text>
            <text x={padding.left + chartWidth / 2} y={height - 10} textAnchor="middle" fontSize="13" fill="#4b5563" fontWeight="600">
              Дата анализа
            </text>
          </svg>
        </div>

        {/* Legend — horizontal on mobile, vertical on desktop */}
        <div className="flex flex-row flex-wrap gap-x-4 gap-y-1.5 md:flex-col md:gap-3 text-xs sm:text-sm shrink-0 md:pt-10">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-emerald-500 shrink-0"></div>
            <span className="text-gray-700">В норме</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-yellow-500 shrink-0"></div>
            <span className="text-gray-700">Близко к границе</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500 shrink-0"></div>
            <span className="text-gray-700">Вне нормы</span>
          </div>
          {(referenceMin !== null && referenceMax !== null) && (
            <>
              <div className="flex items-center gap-2">
                <div className="w-4 h-3 rounded-sm shrink-0" style={{ backgroundColor: 'rgba(16, 185, 129, 0.2)' }}></div>
                <span className="text-gray-700">Зона нормы</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-8 h-0.5 shrink-0 bg-red-500" style={{ backgroundImage: 'repeating-linear-gradient(to right, #ef4444 0, #ef4444 6px, transparent 6px, transparent 9px)' }}></div>
                <span className="text-gray-700">Границы нормы</span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Data Table */}
      <div className="overflow-hidden rounded-lg sm:rounded-xl border border-gray-200">
        <div className="bg-gradient-to-r from-gray-50 to-gray-100 px-3 sm:px-6 py-2 sm:py-3 border-b border-gray-200 flex items-center justify-between">
          <h4 className="text-xs sm:text-sm font-semibold text-gray-900">Таблица значений</h4>
          {excludedPoints.size > 0 && (
            <span className="text-xs text-gray-600">
              Исключено: {excludedPoints.size} из {points.filter((p) => typeof p.value_num === 'number' && p.date).length}
            </span>
          )}
        </div>
        <div className="max-h-80 overflow-x-auto overflow-y-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                <th className="px-2 sm:px-6 py-2 sm:py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Включить
                </th>
                <th className="px-2 sm:px-6 py-2 sm:py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider hidden sm:table-cell">
                  №
                </th>
                <th className="px-2 sm:px-6 py-2 sm:py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Дата
                </th>
                <th className="px-2 sm:px-6 py-2 sm:py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Значение
                </th>
                <th className="px-2 sm:px-6 py-2 sm:py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider hidden sm:table-cell">
                  Отклонение от среднего
                </th>
                <th className="px-2 sm:px-4 py-2 sm:py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Документ
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {points
                .filter((p) => typeof p.value_num === 'number' && p.date)
                .sort((a, b) => new Date(b.date || '').getTime() - new Date(a.date || '').getTime())
                .map((p, originalIndex) => {
                  const isExcluded = excludedPoints.has(p._id || '')
                  const deviationValue = isExcluded ? 0 : ((p.value_num - avgValue) / avgValue * 100)
                  const deviation = deviationValue.toFixed(1)
                  const isAboveAvg = p.value_num > avgValue
                  const pointIndex = data.findIndex(d => d._id === p._id)

                  return (
                    <tr
                      key={p._id || originalIndex}
                      className={`hover:bg-gray-50 transition-colors ${isExcluded ? 'opacity-50 bg-gray-50' : ''} ${p.document_id ? 'cursor-pointer' : ''}`}
                      onMouseEnter={() => !isExcluded && pointIndex !== -1 && setHoveredPoint(pointIndex)}
                      onMouseLeave={() => setHoveredPoint(null)}
                      onClick={() => p.document_id && onOpenDocument(p.document_id)}
                    >
                      <td className="px-2 sm:px-6 py-1.5 sm:py-4 whitespace-nowrap">
                        <label className="flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={!isExcluded}
                            onChange={() => onTogglePoint(p._id || '')}
                            className="w-4 h-4 text-[#4A90E2] border-gray-300 rounded focus:ring-[#4A90E2] focus:ring-2 cursor-pointer"
                            onClick={(e) => e.stopPropagation()}
                          />
                        </label>
                      </td>
                      <td className={`px-2 sm:px-6 py-1.5 sm:py-4 whitespace-nowrap text-xs sm:text-sm font-medium hidden sm:table-cell ${isExcluded ? 'text-gray-400 line-through' : 'text-gray-900'}`}>
                        {points.filter((p) => typeof p.value_num === 'number' && p.date).length - originalIndex}
                      </td>
                      <td className={`px-2 sm:px-6 py-1.5 sm:py-4 whitespace-nowrap text-xs sm:text-sm ${isExcluded ? 'text-gray-400 line-through' : 'text-gray-700'}`}>
                        {formatDate(new Date(p.date!).getTime())}
                      </td>
                      <td className={`px-2 sm:px-6 py-1.5 sm:py-4 whitespace-nowrap ${isExcluded ? 'text-gray-400 line-through' : ''}`}>
                        <span className={`text-xs sm:text-sm font-semibold ${isExcluded ? 'text-gray-400' : 'text-gray-900'}`}>
                          {formatValue(p.value_num)} {displayUnit}
                        </span>
                      </td>
                      <td className="px-2 sm:px-6 py-1.5 sm:py-4 whitespace-nowrap hidden sm:table-cell">
                        {!isExcluded ? (
                          <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
                            Math.abs(parseFloat(deviation)) < 5
                              ? 'bg-emerald-100 text-emerald-800'
                              : isAboveAvg
                              ? 'bg-orange-100 text-orange-800'
                              : 'bg-blue-100 text-blue-800'
                          }`}>
                            {isAboveAvg ? '↑' : '↓'} {Math.abs(parseFloat(deviation))}%
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-2 sm:px-4 py-1.5 sm:py-4 whitespace-nowrap">
                        {p.document_id ? (
                          <button
                            onClick={(e) => { e.stopPropagation(); onOpenDocument(p.document_id!) }}
                            className="flex items-center gap-1 text-[#4A90E2] hover:text-blue-700 transition-colors"
                            title="Открыть документ"
                          >
                            <FileText className="w-4 h-4" />
                          </button>
                        ) : (
                          <span className="text-xs text-gray-300">—</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
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

  useEffect(() => {
    if (selectedAnalyte) {
      for (const category of categories) {
        if (category.analytes.some(a => a.canonical_name === selectedAnalyte)) {
          setExpandedCategories(prev => new Set([...prev, category.name]))
          break
        }
      }
    }
  }, [selectedAnalyte, categories])

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
                className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-gray-50 transition-colors"
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
                      className={`w-full flex items-center justify-between px-4 py-2 text-left hover:bg-gray-100 transition-colors ${
                        selectedAnalyte === analyte.canonical_name
                          ? 'bg-blue-50 border-l-2 border-l-blue-500'
                          : 'border-l-2 border-l-transparent'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className={`text-sm ${selectedAnalyte === analyte.canonical_name ? 'font-medium text-blue-900' : 'text-gray-700'}`}>
                          {analyte.canonical_name}
                        </span>
                        {analyte.standard_unit && (
                          <span className="text-xs text-gray-500">({analyte.standard_unit})</span>
                        )}
                      </div>
                      <span className="text-xs text-gray-400">{analyte.count} изм.</span>
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
  const [isSelectorExpanded, setIsSelectorExpanded] = useState(false)

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

  useEffect(() => {
    setExcludedPoints(new Set())
  }, [selected])

  useEffect(() => {
    if (!selected && categories.length > 0) {
      const firstCategory = categories[0]
      if (firstCategory.analytes.length > 0) {
        setSelected(firstCategory.analytes[0].canonical_name)
      }
    }
  }, [categories, selected])

  const togglePoint = (pointId: string) => {
    setExcludedPoints(prev => {
      const newSet = new Set(prev)
      if (newSet.has(pointId)) newSet.delete(pointId)
      else newSet.add(pointId)
      return newSet
    })
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

      {/* Analyte selector — collapsible on mobile */}
      <div className="medical-card">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-lg shrink-0">🧪</span>
            <h3 className="text-sm sm:text-base font-semibold text-gray-900 truncate">
              {isSelectorExpanded || !selected ? 'Выберите анализ' : selected}
            </h3>
          </div>
          <button
            onClick={() => setIsSelectorExpanded(prev => !prev)}
            className="lg:hidden ml-2 shrink-0 text-xs font-medium px-2.5 py-1 rounded-lg border border-blue-100 bg-blue-50 text-blue-600 active:bg-blue-100 transition-colors"
          >
            {isSelectorExpanded ? 'Свернуть' : (selected ? 'Сменить' : 'Выбрать')}
          </button>
        </div>

        {/* Compact meta when collapsed on mobile */}
        {!isSelectorExpanded && selected && seriesData && (
          <div className="lg:hidden flex flex-wrap gap-1.5 mb-1">
            {seriesData.standard_unit && (
              <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded-md border border-blue-100">
                {seriesData.standard_unit}
              </span>
            )}
            {seriesData.category && (
              <span className="text-xs px-2 py-0.5 bg-purple-50 text-purple-600 rounded-md border border-purple-100">
                {seriesData.category}
              </span>
            )}
          </div>
        )}

        <div className={isSelectorExpanded ? 'block' : 'hidden lg:block'}>
          {loadingAnalytes ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#4A90E2]"></div>
            </div>
          ) : categories.length > 0 ? (
            <AnalyteSelector
              categories={categories}
              selectedAnalyte={selected}
              onSelect={(name) => {
                setSelected(name)
                setIsSelectorExpanded(false)
              }}
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
      <div className="medical-card">
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
          </div>
        ) : (
          <div className="text-center py-12">
            <div className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4 rounded-full bg-gray-100 flex items-center justify-center">
              <span className="text-2xl sm:text-3xl">📈</span>
            </div>
            <p className="text-xs sm:text-sm text-gray-500">
              {selected ? 'Нет данных для отображения' : 'Выберите анализ для просмотра'}
            </p>
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
