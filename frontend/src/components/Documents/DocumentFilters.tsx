import { useState, useEffect, useMemo, useCallback } from 'react'
import { Filter, X } from 'lucide-react'
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
}

export default function DocumentFilters({ filters, onChange, onReset }: DocumentFiltersProps) {
  // State for filter values
  const [documentTypeValues, setDocumentTypeValues] = useState<string[]>([])
  const [specialtiesValues, setSpecialtiesValues] = useState<string[]>([])
  const [documentSubtypeValues, setDocumentSubtypeValues] = useState<string[]>([])
  const [researchAreaValues, setResearchAreaValues] = useState<string[]>([])
  const [medicalFacilityValues, setMedicalFacilityValues] = useState<string[]>([])
  const [patientNameValues, setPatientNameValues] = useState<string[]>([])
  
  // Loading states
  const [loadingStates, setLoadingStates] = useState({
    specialties: false,
    document_subtype: false,
    research_area: false,
    medical_facility: false,
    patient_name: false,
    document_type: false
  })

  // Fetch filter values - обернуто в useCallback для предотвращения бесконечного цикла
  const fetchFilterValues = useCallback(async (field: string, query?: string) => {
    try {
      setLoadingStates(prev => ({ ...prev, [field]: true }))
      const values = await documentsService.getFilterValues(field, query, 50)
      
      switch (field) {
        case 'document_type':
          setDocumentTypeValues(values)
          break
        case 'specialties':
          setSpecialtiesValues(values)
          break
        case 'document_subtype':
          setDocumentSubtypeValues(values)
          break
        case 'research_area':
          setResearchAreaValues(values)
          break
        case 'medical_facility':
          setMedicalFacilityValues(values)
          break
        case 'patient_name':
          setPatientNameValues(values)
          break
      }
    } catch (error) {
      console.error(`Error fetching ${field} values:`, error)
    } finally {
      setLoadingStates(prev => ({ ...prev, [field]: false }))
    }
  }, [])


  // Мемоизированные обработчики поиска для каждого поля
  const handleSearchSpecialties = useCallback((q: string) => fetchFilterValues('specialties', q), [fetchFilterValues])
  const handleSearchDocumentSubtype = useCallback((q: string) => fetchFilterValues('document_subtype', q), [fetchFilterValues])
  const handleSearchResearchArea = useCallback((q: string) => fetchFilterValues('research_area', q), [fetchFilterValues])
  const handleSearchMedicalFacility = useCallback((q: string) => fetchFilterValues('medical_facility', q), [fetchFilterValues])
  const handleSearchPatientName = useCallback((q: string) => fetchFilterValues('patient_name', q), [fetchFilterValues])

  // Initial load of all filters
  useEffect(() => {
    fetchFilterValues('document_type')
    fetchFilterValues('medical_facility')
    fetchFilterValues('patient_name')
    fetchFilterValues('specialties')
    fetchFilterValues('document_subtype')
    fetchFilterValues('research_area')
  }, [fetchFilterValues])

  const handleChange = (field: keyof DocumentFilterValues, value: any) => {
    onChange({
      ...filters,
      [field]: value && (Array.isArray(value) ? value.length > 0 : value) ? value : undefined,
    })
  }

  const handleReset = () => {
    if (onReset) {
      onReset()
    } else {
      onChange({})
    }
  }

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => {
    return Object.values(filters).some(v => {
      if (Array.isArray(v)) return v.length > 0
      return !!v
    })
  }, [filters])

  return (
    <div className="bg-white shadow rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Filter className="h-5 w-5 text-gray-500" />
          <h3 className="text-sm font-medium text-gray-900">Фильтры</h3>
          {hasActiveFilters && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800">
              Активны
            </span>
          )}
        </div>
        {hasActiveFilters && (
          <button
            onClick={handleReset}
            className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
          >
            <X className="h-4 w-4" />
            Сбросить
          </button>
        )}
      </div>

      <div className="space-y-3">
        {/* Основные фильтры */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {/* Тип документа */}
          <MultiSelect
            label="Тип документа"
            placeholder="Все типы"
            values={documentTypeValues}
            selectedValues={filters.document_type || []}
            onChange={(values) => handleChange('document_type', values)}
            loading={loadingStates.document_type}
          />

          {/* Имя пациента */}
          <MultiSelect
            label="Имя пациента"
            placeholder="Все пациенты"
            values={patientNameValues}
            selectedValues={filters.patient_name || []}
            onChange={(values) => handleChange('patient_name', values)}
            onSearch={handleSearchPatientName}
            loading={loadingStates.patient_name}
          />

          {/* Медицинское учреждение */}
          <MultiSelect
            label="Медучреждение"
            placeholder="Все учреждения"
            values={medicalFacilityValues}
            selectedValues={filters.medical_facility || []}
            onChange={(values) => handleChange('medical_facility', values)}
            onSearch={handleSearchMedicalFacility}
            loading={loadingStates.medical_facility}
          />

          {/* Специализация */}
          <MultiSelect
            label="Специализация"
            placeholder="Все специализации"
            values={specialtiesValues}
            selectedValues={filters.specialties || []}
            onChange={(values) => handleChange('specialties', values)}
            onSearch={handleSearchSpecialties}
            loading={loadingStates.specialties}
          />

          {/* Подтип документа */}
          <MultiSelect
            label="Подтип документа"
            placeholder="Все подтипы"
            values={documentSubtypeValues}
            selectedValues={filters.document_subtype || []}
            onChange={(values) => handleChange('document_subtype', values)}
            onSearch={handleSearchDocumentSubtype}
            loading={loadingStates.document_subtype}
          />

          {/* Область исследования */}
          <MultiSelect
            label="Область исследования"
            placeholder="Все области"
            values={researchAreaValues}
            selectedValues={filters.research_area || []}
            onChange={(values) => handleChange('research_area', values)}
            onSearch={handleSearchResearchArea}
            loading={loadingStates.research_area}
          />
        </div>

        {/* Диапазоны дат */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {/* Дата документа */}
          <DateRangePicker
            label="Дата документа"
            fromValue={filters.date_from || ''}
            toValue={filters.date_to || ''}
            onFromChange={(value) => handleChange('date_from', value || undefined)}
            onToChange={(value) => handleChange('date_to', value || undefined)}
          />

          {/* Дата загрузки */}
          <DateRangePicker
            label="Дата загрузки"
            fromValue={filters.created_from || ''}
            toValue={filters.created_to || ''}
            onFromChange={(value) => handleChange('created_from', value || undefined)}
            onToChange={(value) => handleChange('created_to', value || undefined)}
          />
        </div>
      </div>
    </div>
  )
}
