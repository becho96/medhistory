import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { healthEventsService } from '../../services/healthEvents'
import { HealthEvent, HealthEventCreate } from '../../types'
import ParameterSelector from './ParameterSelector'
import TagInput from './TagInput'

interface HealthEventModalProps {
  isOpen: boolean
  onClose: () => void
  event?: HealthEvent
  onSuccess: () => void
}

export default function HealthEventModal({ 
  isOpen, 
  onClose, 
  event, 
  onSuccess 
}: HealthEventModalProps) {
  const [eventDatetime, setEventDatetime] = useState('')
  const [parameters, setParameters] = useState<Record<string, any>>({})
  const [tags, setTags] = useState<string[]>([])
  const [notes, setNotes] = useState('')
  
  const queryClient = useQueryClient()
  
  // Загрузка при редактировании
  useEffect(() => {
    if (event) {
      setEventDatetime(event.event_datetime.slice(0, 16))
      setParameters(event.parameters)
      setTags(event.tags)
      setNotes(event.notes || '')
    } else {
      // Сброс при создании нового
      const now = new Date()
      setEventDatetime(now.toISOString().slice(0, 16))
      setParameters({})
      setTags([])
      setNotes('')
    }
  }, [event, isOpen])
  
  // Загрузка библиотеки параметров
  const { data: definitions } = useQuery({
    queryKey: ['health-parameters'],
    queryFn: () => healthEventsService.getParameterDefinitions()
  })
  
  // Мутация создания/обновления
  const mutation = useMutation({
    mutationFn: (data: HealthEventCreate) => 
      event 
        ? healthEventsService.updateHealthEvent(event.id, data)
        : healthEventsService.createHealthEvent(data),
    onSuccess: () => {
      toast.success(event ? 'Событие обновлено' : 'Событие создано')
      queryClient.invalidateQueries({ queryKey: ['health-events'] })
      onSuccess()
      onClose()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Произошла ошибка')
    }
  })
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!eventDatetime) {
      toast.error('Укажите дату и время события')
      return
    }
    
    mutation.mutate({
      event_datetime: eventDatetime,
      parameters,
      tags,
      notes: notes || undefined
    })
  }
  
  if (!isOpen) return null
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-900">
            {event ? 'Редактировать событие' : 'Новое событие'}
          </h2>
          <button 
            onClick={onClose} 
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Дата и время */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Дата и время события *
            </label>
            <input
              type="datetime-local"
              value={eventDatetime}
              onChange={(e) => setEventDatetime(e.target.value)}
              max={new Date().toISOString().slice(0, 16)}
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          {/* Параметры */}
          {definitions && (
            <ParameterSelector
              definitions={definitions}
              values={parameters}
              onChange={(key, value) => {
                setParameters(prev => {
                  const newParams = { ...prev }
                  if (value === null || value === undefined || value === '') {
                    delete newParams[key]
                  } else {
                    newParams[key] = value
                  }
                  return newParams
                })
              }}
            />
          )}
          
          {/* Теги */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Теги
            </label>
            <TagInput
              tags={tags}
              onChange={setTags}
              placeholder="Добавить тег..."
            />
            <p className="text-xs text-gray-500 mt-1">
              Нажмите Enter для добавления тега
            </p>
          </div>
          
          {/* Заметки */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Заметки
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={4}
              placeholder="Дополнительные комментарии..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          {/* Кнопки */}
          <div className="flex gap-3 justify-end pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {mutation.isPending ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
