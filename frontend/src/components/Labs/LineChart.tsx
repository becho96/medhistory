import { useState } from 'react'
import { FileText } from 'lucide-react'

export interface ChartPoint {
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

export default function LineChart({ points, excludedPoints, onTogglePoint, onOpenDocument, standardUnit, referenceMin, referenceMax }: LineChartProps) {
  const [hoveredPoint, setHoveredPoint] = useState<number | null>(null)
  const width = 760
  const height = 420
  const padding = { top: 40, right: 28, bottom: 70, left: 62 }

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
  const tablePoints = points
    .filter((p) => typeof p.value_num === 'number' && p.date)
    .sort((a, b) => new Date(b.date || '').getTime() - new Date(a.date || '').getTime())

  return (
    <div className="space-y-4 sm:space-y-6">
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

            {data.length >= 2 && (
              <>
                <line x1={padding.left} y1={yScale(minValue)} x2={width - padding.right} y2={yScale(minValue)} stroke="#9ca3af" strokeWidth="1" opacity="0.7" />
                <text x={width - padding.right - 5} y={yScale(minValue) - 5} textAnchor="end" fontSize="11" fill="#6b7280" fontWeight="500">
                  Мин: {formatValue(minValue)} {displayUnit}
                </text>

                <line x1={padding.left} y1={yScale(maxValue)} x2={width - padding.right} y2={yScale(maxValue)} stroke="#9ca3af" strokeWidth="1" opacity="0.7" />
                <text x={width - padding.right - 5} y={yScale(maxValue) - 5} textAnchor="end" fontSize="11" fill="#6b7280" fontWeight="500">
                  Макс: {formatValue(maxValue)} {displayUnit}
                </text>

                <line x1={padding.left} y1={yScale(avgValue)} x2={width - padding.right} y2={yScale(avgValue)} stroke="#4b5563" strokeWidth="1" strokeDasharray="4,4" opacity="0.7" />
                <text x={width - padding.right - 5} y={yScale(avgValue) - 5} textAnchor="end" fontSize="11" fill="#4b5563" fontWeight="500">
                  Сред: {formatValue(avgValue)} {displayUnit}
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
            <div className="flex items-center gap-2">
              <div className="w-4 h-3 rounded-sm shrink-0" style={{ backgroundColor: 'rgba(16, 185, 129, 0.2)' }}></div>
              <span className="text-gray-700">Зона нормы</span>
            </div>
          )}
          {data.length >= 2 && (
            <>
              <div className="flex items-center gap-2">
                <div className="w-8 h-px shrink-0 bg-gray-400"></div>
                <span className="text-gray-700">Мин/Макс по измерениям</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-8 h-px shrink-0" style={{ backgroundImage: 'repeating-linear-gradient(to right, #4b5563 0, #4b5563 4px, transparent 4px, transparent 8px)' }}></div>
                <span className="text-gray-700">Среднее</span>
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
        <div className="sm:hidden max-h-80 overflow-y-auto divide-y divide-gray-100 bg-white">
          {tablePoints.map((p, originalIndex) => {
            const isExcluded = excludedPoints.has(p._id || '')
            const deviationValue = isExcluded ? 0 : ((p.value_num - avgValue) / avgValue * 100)
            const deviation = deviationValue.toFixed(1)
            const isAboveAvg = p.value_num > avgValue
            const pointIndex = data.findIndex(d => d._id === p._id)

            return (
              <div
                key={p._id || originalIndex}
                className={`p-3 ${isExcluded ? 'bg-gray-50 opacity-60' : 'bg-white'} ${p.document_id ? 'cursor-pointer' : ''}`}
                onMouseEnter={() => !isExcluded && pointIndex !== -1 && setHoveredPoint(pointIndex)}
                onMouseLeave={() => setHoveredPoint(null)}
                onClick={() => p.document_id && onOpenDocument(p.document_id)}
              >
                <div className="flex items-start justify-between gap-3">
                  <label className="flex min-h-11 min-w-11 items-center justify-center rounded-xl border border-gray-200 bg-white" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={!isExcluded}
                      onChange={() => onTogglePoint(p._id || '')}
                      className="h-5 w-5 cursor-pointer rounded border-gray-300 text-[#4A90E2] focus:ring-[#4A90E2]"
                    />
                  </label>
                  <div className="min-w-0 flex-1">
                    <p className={`text-sm font-medium ${isExcluded ? 'text-gray-400 line-through' : 'text-gray-900'}`}>
                      {formatDate(new Date(p.date!).getTime())}
                    </p>
                    <p className={`mt-1 text-lg font-semibold ${isExcluded ? 'text-gray-400 line-through' : 'text-gray-900'}`}>
                      {formatValue(p.value_num)} {displayUnit}
                    </p>
                    {!isExcluded && (
                      <p className={`mt-1 text-xs ${Math.abs(parseFloat(deviation)) < 5 ? 'text-emerald-700' : isAboveAvg ? 'text-orange-700' : 'text-blue-700'}`}>
                        {isAboveAvg ? 'Выше среднего' : 'Ниже среднего'} на {Math.abs(parseFloat(deviation))}%
                      </p>
                    )}
                  </div>
                  {p.document_id && (
                    <button
                      onClick={(e) => { e.stopPropagation(); onOpenDocument(p.document_id!) }}
                      className="flex min-h-11 min-w-11 items-center justify-center rounded-xl text-[#4A90E2] hover:bg-blue-50"
                      aria-label="Открыть документ"
                    >
                      <FileText className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
        <div className="hidden sm:block max-h-80 overflow-x-auto overflow-y-auto">
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
              {tablePoints.map((p, originalIndex) => {
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
                        {tablePoints.length - originalIndex}
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
