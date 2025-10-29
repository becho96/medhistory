import { useState, useRef, useEffect } from 'react'
import { X, ChevronDown } from 'lucide-react'

interface MultiSelectProps {
  label: string
  placeholder?: string
  values: string[]
  selectedValues: string[]
  onChange: (selected: string[]) => void
  onSearch?: (query: string) => void
  loading?: boolean
  disabled?: boolean
}

export default function MultiSelect({
  label,
  placeholder = 'Выберите...',
  values,
  selectedValues,
  onChange,
  onSearch,
  loading = false,
  disabled = false
}: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Trigger search callback - только если есть поисковый запрос
  useEffect(() => {
    if (onSearch && searchQuery) {
      const timer = setTimeout(() => {
        onSearch(searchQuery)
      }, 300)
      return () => clearTimeout(timer)
    }
  }, [searchQuery, onSearch])

  const handleToggle = () => {
    if (!disabled) {
      setIsOpen(!isOpen)
      if (!isOpen) {
        setTimeout(() => inputRef.current?.focus(), 100)
      }
    }
  }

  const handleSelect = (value: string) => {
    if (selectedValues.includes(value)) {
      onChange(selectedValues.filter(v => v !== value))
    } else {
      onChange([...selectedValues, value])
    }
  }

  const handleRemove = (value: string, e: React.MouseEvent) => {
    e.stopPropagation()
    onChange(selectedValues.filter(v => v !== value))
  }

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation()
    onChange([])
  }

  // Filter values based on search query
  const filteredValues = values.filter(v =>
    v.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="relative" ref={containerRef}>
      <label className="block text-xs font-medium text-gray-700 mb-1">
        {label}
      </label>

      {/* Selected values (chips) */}
      {selectedValues.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {selectedValues.map(value => (
            <span
              key={value}
              className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-primary-100 text-primary-800"
            >
              {value}
              <button
                type="button"
                onClick={(e) => handleRemove(value, e)}
                className="ml-1 hover:text-primary-900"
                disabled={disabled}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
          <button
            type="button"
            onClick={handleClear}
            className="text-xs text-gray-500 hover:text-gray-700 underline"
            disabled={disabled}
          >
            Очистить все
          </button>
        </div>
      )}

      {/* Input field */}
      <div
        className={`relative w-full px-3 py-2 text-sm border rounded-md cursor-pointer ${
          disabled
            ? 'bg-gray-100 cursor-not-allowed'
            : isOpen
            ? 'border-primary-500 ring-1 ring-primary-500'
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onClick={handleToggle}
      >
        <div className="flex items-center justify-between">
          <input
            ref={inputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onClick={(e) => {
              e.stopPropagation()
              setIsOpen(true)
            }}
            placeholder={selectedValues.length === 0 ? placeholder : 'Поиск...'}
            className="flex-1 outline-none bg-transparent"
            disabled={disabled}
          />
          <ChevronDown
            className={`h-4 w-4 text-gray-400 transition-transform ${
              isOpen ? 'transform rotate-180' : ''
            }`}
          />
        </div>
      </div>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
          {loading ? (
            <div className="px-3 py-2 text-sm text-gray-500 text-center">
              Загрузка...
            </div>
          ) : filteredValues.length === 0 ? (
            <div className="px-3 py-2 text-sm text-gray-500 text-center">
              {searchQuery ? 'Ничего не найдено' : 'Нет доступных значений'}
            </div>
          ) : (
            <ul className="py-1">
              {filteredValues.map(value => (
                <li
                  key={value}
                  className={`px-3 py-2 text-sm cursor-pointer hover:bg-gray-100 ${
                    selectedValues.includes(value) ? 'bg-primary-50 text-primary-700 font-medium' : 'text-gray-900'
                  }`}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleSelect(value)
                  }}
                >
                  <div className="flex items-center justify-between">
                    <span>{value}</span>
                    {selectedValues.includes(value) && (
                      <span className="text-primary-600">✓</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

