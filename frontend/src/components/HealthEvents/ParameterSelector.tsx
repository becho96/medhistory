import { useState } from 'react'
import { ParameterDefinition } from '../../types'
import ParameterField from './ParameterField'
import { Search } from 'lucide-react'

interface ParameterSelectorProps {
  definitions: ParameterDefinition[]
  values: Record<string, any>
  onChange: (key: string, value: any) => void
}

export default function ParameterSelector({ 
  definitions, 
  values, 
  onChange 
}: ParameterSelectorProps) {
  const [searchQuery, setSearchQuery] = useState('')
  
  const primaryParams = definitions.filter(d => d.is_primary)
  const secondaryParams = definitions.filter(d => !d.is_primary)
  
  const filteredSecondary = secondaryParams.filter(param =>
    param.label_ru.toLowerCase().includes(searchQuery.toLowerCase())
  )
  
  return (
    <div className="space-y-6">
      {/* 7 основных параметров */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-3">
          Основные параметры
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {primaryParams.map(param => (
            <ParameterField
              key={param.key}
              definition={param}
              value={values[param.key]}
              onChange={(value) => onChange(param.key, value)}
            />
          ))}
        </div>
      </div>
      
      {/* Поиск дополнительных параметров */}
      <div className="border-t pt-6">
        <h3 className="text-sm font-medium text-gray-700 mb-3">
          Дополнительные параметры
        </h3>
        
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Поиск параметров..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        
        {searchQuery && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredSecondary.map(param => (
              <ParameterField
                key={param.key}
                definition={param}
                value={values[param.key]}
                onChange={(value) => onChange(param.key, value)}
              />
            ))}
          </div>
        )}
        
        {searchQuery && filteredSecondary.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-8">
            Параметры не найдены
          </p>
        )}
        
        {!searchQuery && (
          <p className="text-sm text-gray-500 text-center py-4">
            Начните вводить название параметра для поиска
          </p>
        )}
      </div>
    </div>
  )
}
