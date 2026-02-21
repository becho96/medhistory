import { Edit2, Trash2, Calendar, MessageCircle } from 'lucide-react'
import { HealthEvent, ParameterDefinition } from '../../types'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'

interface HealthEventCardProps {
  event: HealthEvent
  definitions?: ParameterDefinition[]
  onEdit: () => void
  onDelete: () => void
}

export default function HealthEventCard({ 
  event, 
  definitions,
  onEdit, 
  onDelete 
}: HealthEventCardProps) {
  // Создаем map для быстрого поиска определений
  const definitionsMap = definitions?.reduce((acc, def) => {
    acc[def.key] = def
    return acc
  }, {} as Record<string, ParameterDefinition>) || {}
  
  // Форматирование значения параметра
  const formatParameterValue = (key: string, value: any): string => {
    const definition = definitionsMap[key]
    if (!definition) return String(value)
    
    if (definition.type === 'number' && definition.config.unit) {
      return `${value}${definition.config.unit}`
    }
    
    if (definition.type === 'scale' && definition.config.options) {
      const option = definition.config.options.find(opt => opt.value === value)
      return option?.label || String(value)
    }
    
    if (definition.type === 'boolean') {
      return value ? 'Да' : 'Нет'
    }
    
    return String(value)
  }
  
  // Получаем основные параметры для отображения
  const displayParams = Object.entries(event.parameters)
    .filter(([key]) => definitionsMap[key])
    .slice(0, 5)
  
  const hasMoreParams = Object.keys(event.parameters).length > 5
  
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-md transition-shadow">
      {/* Хедер */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-2 text-gray-600">
          <Calendar className="w-5 h-5" />
          <span className="font-medium">
            {format(new Date(event.event_datetime), 'dd MMMM yyyy, HH:mm', { locale: ru })}
          </span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onEdit}
            className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            title="Редактировать"
          >
            <Edit2 className="w-4 h-4" />
          </button>
          <button
            onClick={onDelete}
            className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            title="Удалить"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      {/* Параметры */}
      {displayParams.length > 0 && (
        <div className="mb-4 space-y-2">
          {displayParams.map(([key, value]) => (
            <div key={key} className="flex justify-between text-sm">
              <span className="text-gray-600">{definitionsMap[key]?.label_ru || key}:</span>
              <span className="font-medium text-gray-900">
                {formatParameterValue(key, value)}
              </span>
            </div>
          ))}
          {hasMoreParams && (
            <p className="text-sm text-gray-500 italic">
              + еще {Object.keys(event.parameters).length - 5} параметр(ов)
            </p>
          )}
        </div>
      )}
      
      {/* Теги */}
      {event.tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {event.tags.map(tag => (
            <span 
              key={tag} 
              className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
      
      {/* Заметки */}
      {event.notes && (
        <div className="pt-4 border-t border-gray-100">
          <div className="flex items-start gap-2">
            <MessageCircle className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-gray-600 whitespace-pre-wrap">
              {event.notes}
            </p>
          </div>
        </div>
      )}
      
      {/* Если нет параметров */}
      {displayParams.length === 0 && !event.notes && event.tags.length === 0 && (
        <p className="text-sm text-gray-400 italic">
          Нет данных для отображения
        </p>
      )}
    </div>
  )
}
