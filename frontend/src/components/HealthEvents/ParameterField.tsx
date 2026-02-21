import { ParameterDefinition } from '../../types'

interface ParameterFieldProps {
  definition: ParameterDefinition
  value: any
  onChange: (value: any) => void
}

export default function ParameterField({ 
  definition, 
  value, 
  onChange 
}: ParameterFieldProps) {
  const { type, label_ru, config } = definition
  
  // Number type
  if (type === 'number') {
    return (
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label_ru}
          {config.unit && <span className="text-gray-500 ml-1">({config.unit})</span>}
        </label>
        <input
          type="number"
          value={value ?? ''}
          onChange={(e) => onChange(parseFloat(e.target.value) || null)}
          min={config.min}
          max={config.max}
          step={config.step}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>
    )
  }
  
  // Scale type (с options)
  if (type === 'scale' && config.options) {
    return (
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label_ru}
        </label>
        <select
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value || null)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">Не указано</option>
          {config.options.map(opt => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
    )
  }
  
  // Scale type (с min/max - slider)
  if (type === 'scale' && config.min !== undefined && config.max !== undefined) {
    return (
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label_ru}: {value ?? 'Не указано'}
        </label>
        <input
          type="range"
          value={value ?? config.min}
          onChange={(e) => onChange(parseInt(e.target.value))}
          min={config.min}
          max={config.max}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>{config.labels?.[config.min] || config.min}</span>
          <span>{config.labels?.[config.max] || config.max}</span>
        </div>
      </div>
    )
  }
  
  // Text type
  if (type === 'text') {
    return (
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label_ru}
        </label>
        <input
          type="text"
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value || null)}
          placeholder={config.placeholder}
          pattern={config.pattern}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>
    )
  }
  
  // Boolean type
  if (type === 'boolean') {
    return (
      <div className="flex items-center gap-3">
        <input
          type="checkbox"
          checked={value ?? false}
          onChange={(e) => onChange(e.target.checked)}
          className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
        <label className="text-sm font-medium text-gray-700">
          {label_ru}
        </label>
      </div>
    )
  }
  
  return null
}
