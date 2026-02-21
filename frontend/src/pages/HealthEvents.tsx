import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Calendar } from 'lucide-react'
import { toast } from 'sonner'
import { healthEventsService } from '../services/healthEvents'
import { HealthEvent } from '../types'
import HealthEventModal from '../components/HealthEvents/HealthEventModal'
import HealthEventCard from '../components/HealthEvents/HealthEventCard'

export default function HealthEvents() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState<HealthEvent | undefined>()
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  
  const queryClient = useQueryClient()
  
  // Загрузка событий
  const { data, isLoading } = useQuery({
    queryKey: ['health-events', { dateFrom, dateTo }],
    queryFn: () => healthEventsService.getHealthEvents({ 
      date_from: dateFrom || undefined, 
      date_to: dateTo || undefined
    })
  })
  
  // Загрузка определений для отображения
  const { data: definitions } = useQuery({
    queryKey: ['health-parameters'],
    queryFn: () => healthEventsService.getParameterDefinitions()
  })
  
  const deleteMutation = useMutation({
    mutationFn: healthEventsService.deleteHealthEvent,
    onSuccess: () => {
      toast.success('Событие удалено')
      queryClient.invalidateQueries({ queryKey: ['health-events'] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Ошибка при удалении')
    }
  })
  
  const handleDelete = (event: HealthEvent) => {
    if (confirm('Вы уверены, что хотите удалить это событие?')) {
      deleteMutation.mutate(event.id)
    }
  }
  
  return (
    <div className="space-y-6">
      {/* Хедер */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Самочувствие</h1>
          <p className="text-sm text-gray-600 mt-1">
            Отслеживайте свое состояние здоровья
          </p>
        </div>
        <button
          onClick={() => {
            setSelectedEvent(undefined)
            setIsModalOpen(true)
          }}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
        >
          <Plus className="w-5 h-5" />
          Добавить событие
        </button>
      </div>
      
      {/* Фильтры */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              С даты
            </label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              По дату
            </label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          {(dateFrom || dateTo) && (
            <div className="flex items-end">
              <button
                onClick={() => {
                  setDateFrom('')
                  setDateTo('')
                }}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Сбросить
              </button>
            </div>
          )}
        </div>
      </div>
      
      {/* Список событий */}
      {isLoading ? (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : data?.events && data.events.length > 0 ? (
        <div className="space-y-4">
          {data.events.map(event => (
            <HealthEventCard
              key={event.id}
              event={event}
              definitions={definitions}
              onEdit={() => {
                setSelectedEvent(event)
                setIsModalOpen(true)
              }}
              onDelete={() => handleDelete(event)}
            />
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl border-2 border-dashed border-gray-300 p-12">
          <div className="text-center">
            <Calendar className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {dateFrom || dateTo ? 'Событий не найдено' : 'Нет событий'}
            </h3>
            <p className="text-gray-600 mb-6">
              {dateFrom || dateTo 
                ? 'Попробуйте изменить фильтры' 
                : 'Добавьте первое событие для отслеживания самочувствия'}
            </p>
            {!dateFrom && !dateTo && (
              <button
                onClick={() => {
                  setSelectedEvent(undefined)
                  setIsModalOpen(true)
                }}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Plus className="w-5 h-5" />
                Добавить событие
              </button>
            )}
          </div>
        </div>
      )}
      
      {/* Модальное окно */}
      <HealthEventModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedEvent(undefined)
        }}
        event={selectedEvent}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['health-events'] })
        }}
      />
    </div>
  )
}
