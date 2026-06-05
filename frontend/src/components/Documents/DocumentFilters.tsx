import { useState, useEffect, useMemo, useCallback } from 'react'
import { X, ChevronDown, SlidersHorizontal } from 'lucide-react'
import { format, subDays, subMonths, startOfMonth } from 'date-fns'
import MultiSelect from './MultiSelect'
import DateRangePicker from './DateRangePicker'
import { documentsService } from '../../services/documents'

export interface DocumentFilterValues {
  document_type?: string[]
  specialties?: string[]
  document_subtype?: string[]
  research_area?: string[]
  medical_facility?: string[]
  patient_name?: string[]
  date_from?: string
  date_to?: string
  created_from?: string
  created_to?: string
}

interface DocumentFiltersProps {
  filters: DocumentFilterValues
  onChange: (filters: DocumentFilterValues) => void
  onReset?: () => void
  sortBy?: 'document_date' | 'created_at'
  onSortChange?: (sortBy: 'document_date' | 'created_at') => void
}

const DOCUMENT_TYPE_CHIPS = [
  'Прием врача',
  'Результаты анализа',
  'Инструментальное исследование',
  'Функциональная диагностика',
  'Другое',
]

type DatePresetId = 'week' | 'month' | '3months' | 'older'

const DATE_PRESETS: { id: DatePresetId; label: string }[] = [
  { id: 'week',    label: 'Неделя' },
  { id: 'month',   label: 'Месяц' },
  { id: '3months', label: '3 месяца' },
  { id: 'older',   label: 'Раньше' },
]

const computeDateRange = (id: DatePresetId): { date_from?: string; date_to?: string } => {
  const today = new Date()
  const fmt = (d: Date) => format(d, 'yyyy-MM-dd')
  switch (id) {
    case 'week':    return { date_from: fmt(subDays(today, 7)),    date_to: fmt(today) }
    case 'month':   return { date_from: fmt(startOfMonth(today)),  date_to: fmt(today) }
    case '3months': return { date_from: fmt(subMonths(today, 3)), date_to: fmt(today) }
    case 'older':   return { date_from: undefined,                 date_to: fmt(subMonths(today, 3)) }
  }
}

// Computes the union date range from multiple selected presets
const computeUnionDateRange = (presets: DatePresetId[]): { date_from?: string; date_to?: string } => {
  if (presets.length === 0) return { date_from: undefined, date_to: undefined }
  const ranges = presets.map(computeDateRange)
  const hasNoFrom = ranges.some(r => r.date_from === undefined)
  const date_from = hasNoFrom
    ? undefined
    : ranges.map(r => r.date_from!).sort()[0]
  const date_to = ranges.map(r => r.date_to).filter(Boolean).sort().reverse()[0] ?? undefined
  return { date_from, date_to }
}

const ADVANCED_FIELDS: (keyof DocumentFilterValues)[] = [
  'specialties', 'document_subtype', 'research_area',
  'medical_facility', 'patient_name', 'created_from', 'created_to',
]

export default function DocumentFilters({ filters, onChange, onReset, sortBy, onSortChange }: DocumentFiltersProps) {
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false)
  const [isMobileExpanded, setIsMobileExpanded] = useState(false)
  const [selectedDatePresets, setSelectedDatePresets] = useState<DatePresetId[]>([])

  const [specialtiesValues, setSpecialtiesValues] = useState<string[]>([])
  const [documentSubtypeValues, setDocumentSubtypeValues] = useState<string[]>([])
  const [researchAreaValues, setResearchAreaValues] = useState<string[]>([])
  const [medicalFacilityValues, setMedicalFacilityValues] = useState<string[]>([])
  const [patientNameValues, setPatientNameValues] = useState<string[]>([])

  const [loadingStates, setLoadingStates] = useState({
    specialties: false,
    document_subtype: false,
    research_area: false,
    medical_facility: false,
    patient_name: false,
  })

  const fetchFilterValues = useCallback(async (field: string, query?: string) => {
    try {
      setLoadingStates(prev => ({ ...prev, [field]: true }))
      const values = await documentsService.getFilterValues(field, query, 50)
      switch (field) {
        case 'specialties': setSpecialtiesValues(values); break
        case 'document_subtype': setDocumentSubtypeValues(values); break
        case 'research_area': setResearchAreaValues(values); break
        case 'medical_facility': setMedicalFacilityValues(values); break
        case 'patient_name': setPatientNameValues(values); break
      }
    } catch (error) {
      // silently ignore fetch errors for filter values
    } finally {
      setLoadingStates(prev => ({ ...prev, [field]: false }))
    }
  }, [])

  const handleSearchSpecialties = useCallback((q: string) => fetchFilterValues('specialties', q), [fetchFilterValues])
  const handleSearchDocumentSubtype = useCallback((q: string) => fetchFilterValues('document_subtype', q), [fetchFilterValues])
  const handleSearchResearchArea = useCallback((q: string) => fetchFilterValues('research_area', q), [fetchFilterValues])
  const handleSearchMedicalFacility = useCallback((q: string) => fetchFilterValues('medical_facility', q), [fetchFilterValues])
  const handleSearchPatientName = useCallback((q: string) => fetchFilterValues('patient_name', q), [fetchFilterValues])

  useEffect(() => {
    fetchFilterValues('medical_facility')
    fetchFilterValues('patient_name')
    fetchFilterValues('specialties')
    fetchFilterValues('document_subtype')
    fetchFilterValues('research_area')
  }, [fetchFilterValues])

  // Auto-open advanced panel if any advanced filter is pre-populated on mount
  useEffect(() => {
    const hasAdvanced = ADVANCED_FIELDS.some(k => {
      const v = filters[k]
      return Array.isArray(v) ? v.length > 0 : !!v
    })
    if (hasAdvanced) setIsAdvancedOpen(true)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleChange = (field: keyof DocumentFilterValues, value: any) => {
    onChange({
      ...filters,
      [field]: value && (Array.isArray(value) ? value.length > 0 : value) ? value : undefined,
    })
  }

  const handleChipToggle = (type: string) => {
    const current = filters.document_type ?? []
    const next = current.includes(type)
      ? current.filter(t => t !== type)
      : [...current, type]
    handleChange('document_type', next.length > 0 ? next : undefined)
  }

  const handleDatePreset = (id: DatePresetId) => {
    const next = selectedDatePresets.includes(id)
      ? selectedDatePresets.filter(p => p !== id)
      : [...selectedDatePresets, id]
    setSelectedDatePresets(next)
    const range = computeUnionDateRange(next)
    onChange({ ...filters, date_from: range.date_from, date_to: range.date_to })
  }

  // Sync preset state when filters are cleared externally
  useEffect(() => {
    if (!filters.date_from && !filters.date_to) {
      setSelectedDatePresets([])
    }
  }, [filters.date_from, filters.date_to])

  const handleReset = () => {
    setSelectedDatePresets([])
    if (onReset) onReset()
    else onChange({})
  }

  const hasActiveFilters = useMemo(() => {
    return Object.values(filters).some(v => Array.isArray(v) ? v.length > 0 : !!v)
  }, [filters])

  const activeAdvancedCount = useMemo(() => {
    return ADVANCED_FIELDS.filter(k => {
      const v = filters[k]
      return Array.isArray(v) ? v.length > 0 : !!v
    }).length
  }, [filters])

  const activeTotalCount = useMemo(() => {
    let n = (filters.document_type ?? []).length > 0 ? 1 : 0
    if (selectedDatePresets.length > 0) n++
    return n + activeAdvancedCount
  }, [filters.document_type, selectedDatePresets, activeAdvancedCount])

  return (
    <div className="bg-white rounded-2xl border border-gray-100 px-4 py-3 space-y-3">
      {/* Mobile toggle row */}
      <div className="flex items-center justify-between lg:hidden">
        <button
          type="button"
          onClick={() => setIsMobileExpanded(v => !v)}
          className="flex min-h-11 items-center gap-2 rounded-xl text-sm font-medium text-gray-600"
        >
          <SlidersHorizontal className="w-4 h-4" />
          Фильтры
          {activeTotalCount > 0 && (
            <span className="px-1.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700">
              {activeTotalCount}
            </span>
          )}
          <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${isMobileExpanded ? 'rotate-180' : ''}`} />
        </button>
        {hasActiveFilters && (
          <button type="button" onClick={handleReset} className="flex min-h-11 items-center gap-1 rounded-xl text-xs text-gray-400">
            <X className="w-3.5 h-3.5" />
            Сбросить
          </button>
        )}
      </div>

      {/* Filter content: hidden on mobile when collapsed, always visible on desktop */}
      <div className={`${isMobileExpanded ? 'block' : 'hidden'} lg:block space-y-3`}>

      {sortBy && onSortChange && (
        <div className="lg:hidden">
          <span className="mb-2 block text-xs font-medium text-gray-400">Сортировка</span>
          <div className="grid grid-cols-2 overflow-hidden rounded-xl border border-gray-200 text-sm font-medium">
            <button
              type="button"
              onClick={() => onSortChange('document_date')}
              className={`min-h-11 px-3 py-2 transition-colors ${
                sortBy === 'document_date'
                  ? 'bg-emerald-500 text-white'
                  : 'bg-white text-gray-600'
              }`}
            >
              По дате документа
            </button>
            <button
              type="button"
              onClick={() => onSortChange('created_at')}
              className={`min-h-11 border-l border-gray-200 px-3 py-2 transition-colors ${
                sortBy === 'created_at'
                  ? 'bg-emerald-500 text-white'
                  : 'bg-white text-gray-600'
              }`}
            >
              По загрузке
            </button>
          </div>
        </div>
      )}

      {/* Tier 1: chip groups */}
      <div className="space-y-2">
        {/* Document type */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-gray-400 w-14 shrink-0">Тип</span>
          {DOCUMENT_TYPE_CHIPS.map(type => {
            const isActive = (filters.document_type ?? []).includes(type)
            return (
              <button
                key={type}
                type="button"
                onClick={() => handleChipToggle(type)}
                className={`min-h-10 px-3 py-2 rounded-full text-sm font-medium transition-colors whitespace-nowrap
                  ${isActive
                    ? 'bg-emerald-500 text-white hover:bg-emerald-600'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
              >
                {type}
              </button>
            )
          })}
        </div>

        {/* Date presets */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-gray-400 w-14 shrink-0">Период</span>
          {DATE_PRESETS.map(({ id, label }) => {
            const isActive = selectedDatePresets.includes(id)
            return (
              <button
                key={id}
                type="button"
                onClick={() => handleDatePreset(id)}
                className={`min-h-10 px-3 py-2 rounded-full text-sm font-medium transition-colors whitespace-nowrap
                  ${isActive
                    ? 'bg-emerald-500 text-white hover:bg-emerald-600'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
              >
                {label}
              </button>
            )
          })}

          {hasActiveFilters && (
            <button
              type="button"
              onClick={handleReset}
              className="flex min-h-10 items-center gap-1 rounded-xl text-sm text-gray-400 hover:text-gray-600 transition-colors ml-1"
            >
              <X className="h-3.5 w-3.5" />
              Сбросить
            </button>
          )}
        </div>
      </div>

      {/* Tier 2: advanced toggle */}
      <div>
        <button
          type="button"
          onClick={() => setIsAdvancedOpen(v => !v)}
          className="flex min-h-10 items-center gap-1.5 rounded-xl text-sm text-gray-400 hover:text-gray-600 transition-colors"
        >
          <ChevronDown className={`h-4 w-4 transition-transform duration-200 ${isAdvancedOpen ? 'rotate-180' : ''}`} />
          Расширенные фильтры
          {!isAdvancedOpen && activeAdvancedCount > 0 && (
            <span className="ml-1 px-1.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">
              {activeAdvancedCount}
            </span>
          )}
        </button>
      </div>

      {/* Tier 3: advanced panel */}
      {isAdvancedOpen && (
        <div className="border-t border-gray-100 pt-3 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <MultiSelect
              label="Специализация"
              placeholder="Все специализации"
              values={specialtiesValues}
              selectedValues={filters.specialties || []}
              onChange={(values) => handleChange('specialties', values)}
              onSearch={handleSearchSpecialties}
              loading={loadingStates.specialties}
            />
            <MultiSelect
              label="Подтип документа"
              placeholder="Все подтипы"
              values={documentSubtypeValues}
              selectedValues={filters.document_subtype || []}
              onChange={(values) => handleChange('document_subtype', values)}
              onSearch={handleSearchDocumentSubtype}
              loading={loadingStates.document_subtype}
            />
            <MultiSelect
              label="Область исследования"
              placeholder="Все области"
              values={researchAreaValues}
              selectedValues={filters.research_area || []}
              onChange={(values) => handleChange('research_area', values)}
              onSearch={handleSearchResearchArea}
              loading={loadingStates.research_area}
            />
            <MultiSelect
              label="Медучреждение"
              placeholder="Все учреждения"
              values={medicalFacilityValues}
              selectedValues={filters.medical_facility || []}
              onChange={(values) => handleChange('medical_facility', values)}
              onSearch={handleSearchMedicalFacility}
              loading={loadingStates.medical_facility}
            />
            <MultiSelect
              label="Имя пациента"
              placeholder="Все пациенты"
              values={patientNameValues}
              selectedValues={filters.patient_name || []}
              onChange={(values) => handleChange('patient_name', values)}
              onSearch={handleSearchPatientName}
              loading={loadingStates.patient_name}
            />
          </div>
          <DateRangePicker
            label="Дата загрузки"
            fromValue={filters.created_from || ''}
            toValue={filters.created_to || ''}
            onFromChange={(value) => handleChange('created_from', value || undefined)}
            onToChange={(value) => handleChange('created_to', value || undefined)}
          />
        </div>
      )}

      </div>{/* end collapsible */}
    </div>
  )
}
