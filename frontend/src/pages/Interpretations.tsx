import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Brain, Loader2, AlertCircle, CheckCircle, Clock, XCircle, Trash2, ChevronDown, ChevronUp, FileText } from 'lucide-react'
import { toast } from 'sonner'
import { interpretationsService } from '../services/interpretations'
import type { Interpretation } from '../types'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'

export default function Interpretations() {
  const queryClient = useQueryClient()
  const [expandedInterpretation, setExpandedInterpretation] = useState<string | null>(null)
  
  // Fetch interpretations
  const { data: interpretationsData, isLoading } = useQuery({
    queryKey: ['interpretations'],
    queryFn: () => interpretationsService.getInterpretations(),
  })
  
  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => interpretationsService.deleteInterpretation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['interpretations'] })
      toast.success('Интерпретация удалена')
    },
    onError: () => {
      toast.error('Ошибка при удалении интерпретации')
    }
  })
  
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'processing':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />
      default:
        return <Clock className="h-5 w-5 text-yellow-500" />
    }
  }
  
  const getStatusBadge = (status: string) => {
    const colors = {
      completed: 'bg-green-100 text-green-700',
      processing: 'bg-blue-100 text-blue-700',
      failed: 'bg-red-100 text-red-700',
      pending: 'bg-yellow-100 text-yellow-700',
    }
    const labels = {
      completed: '✓ Готово',
      processing: '⏳ Обработка',
      failed: '✗ Ошибка',
      pending: '⋯ Ожидание',
    }
    return (
      <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${colors[status as keyof typeof colors] || 'bg-gray-100 text-gray-700'}`}>
        {labels[status as keyof typeof labels] || status}
      </span>
    )
  }
  
  const toggleExpand = (id: string) => {
    setExpandedInterpretation(expandedInterpretation === id ? null : id)
  }
  
  const handleDelete = (interpretation: Interpretation) => {
    if (window.confirm('Вы уверены, что хотите удалить эту интерпретацию?')) {
      deleteMutation.mutate(interpretation.id)
    }
  }
  
  const interpretations = interpretationsData?.items || []
  
  return (
    <div className="space-y-4 md:space-y-8 page-transition">
      {/* Modern Header */}
      <div>
        <div className="flex items-center gap-2 sm:gap-3 mb-2 sm:mb-3">
          <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg sm:rounded-xl bg-gradient-to-br from-purple-100 to-purple-50 flex items-center justify-center shadow-lg shadow-purple-200/50">
            <Brain className="h-5 w-5 sm:h-6 sm:w-6 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-900">AI-Интерпретации</h1>
          </div>
        </div>
        <p className="text-sm sm:text-base md:text-lg text-gray-600 mt-1 sm:mt-2">
          История AI-интерпретаций ваших медицинских анализов
        </p>
      </div>
      
      {/* Important disclaimer */}
      <div className="medical-card bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200">
        <div className="flex gap-3 sm:gap-4">
          <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0">
            <AlertCircle className="h-4 w-4 sm:h-5 sm:w-5 text-amber-600" />
          </div>
          <div className="text-xs sm:text-sm text-amber-900">
            <p className="font-semibold mb-1 sm:mb-2 text-sm sm:text-base">⚠️ Важное напоминание</p>
            <p className="leading-relaxed">
              AI-интерпретации носят информационный характер и НЕ заменяют консультацию врача. 
              Обязательно обсудите результаты с лечащим врачом.
            </p>
          </div>
        </div>
      </div>
      
      {/* Interpretations list */}
      <div className="medical-card">
        {isLoading ? (
          <div className="flex items-center justify-center py-12 sm:py-16">
            <div className="text-center">
              <Loader2 className="h-10 w-10 sm:h-12 sm:w-12 text-[#4A90E2] animate-spin mx-auto mb-3 sm:mb-4" />
              <p className="text-xs sm:text-sm text-gray-600">Загрузка интерпретаций...</p>
            </div>
          </div>
        ) : interpretations.length === 0 ? (
          <div className="text-center py-12 sm:py-16 px-4">
            <div className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4 rounded-full bg-purple-100 flex items-center justify-center">
              <Brain className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
            </div>
            <h3 className="text-sm sm:text-base font-semibold text-gray-900 mb-2">Нет интерпретаций</h3>
            <p className="text-xs sm:text-sm text-gray-500 mb-4 sm:mb-6 max-w-md mx-auto">
              Перейдите на страницу "Медкарта" и выберите анализы для интерпретации
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {interpretations.map((interpretation) => (
              <div key={interpretation.id} className="p-3 sm:p-6 hover:bg-gray-50 transition-colors">
                {/* Header */}
                <div className="flex items-start gap-2 sm:gap-0 sm:justify-between mb-3 sm:mb-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 mb-2">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(interpretation.status)}
                        <h3 className="text-sm sm:text-lg font-semibold text-gray-900 truncate">
                          <span className="hidden sm:inline">Интерпретация от </span>
                          {format(new Date(interpretation.created_at), 'dd MMMM yyyy, HH:mm', { locale: ru })}
                        </h3>
                      </div>
                      {getStatusBadge(interpretation.status)}
                    </div>
                    
                    {/* Documents */}
                    <div className="mt-2 sm:mt-3">
                      <p className="text-xs sm:text-sm font-semibold text-gray-700 mb-1.5 sm:mb-2">
                        📄 Документов: {interpretation.documents.length}
                      </p>
                      <div className="flex flex-wrap gap-1.5 sm:gap-2">
                        {interpretation.documents.map((doc) => (
                          <div
                            key={doc.id}
                            className="inline-flex items-center gap-1.5 sm:gap-2 px-2 sm:px-3 py-1 sm:py-1.5 bg-gray-100 rounded-lg text-xs text-gray-700 hover:bg-gray-200 transition-colors"
                          >
                            <FileText className="h-3 w-3 sm:h-3.5 sm:w-3.5 flex-shrink-0" />
                            <span className="max-w-[150px] sm:max-w-xs truncate font-medium">{doc.original_filename}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                  
                  <button
                    onClick={() => handleDelete(interpretation)}
                    className="ml-2 sm:ml-4 p-1.5 sm:p-2 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors flex-shrink-0"
                    title="Удалить интерпретацию"
                  >
                    <Trash2 className="h-4 w-4 sm:h-5 sm:w-5" />
                  </button>
                </div>
                
                {/* Status-specific content */}
                {interpretation.status === 'completed' && interpretation.interpretation_text && (
                  <div className="mt-3 sm:mt-4">
                    <button
                      onClick={() => toggleExpand(interpretation.id)}
                      className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm font-semibold text-[#4A90E2] hover:text-[#3A7BC8] transition-colors"
                    >
                      {expandedInterpretation === interpretation.id ? (
                        <>
                          <ChevronUp className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                          Скрыть интерпретацию
                        </>
                      ) : (
                        <>
                          <ChevronDown className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                          Показать интерпретацию
                        </>
                      )}
                    </button>
                    
                    {expandedInterpretation === interpretation.id && (
                      <div className="mt-3 sm:mt-4 p-3 sm:p-5 bg-gradient-to-br from-gray-50 to-white rounded-lg sm:rounded-xl border border-gray-200">
                        <div className="prose prose-sm max-w-none">
                          <div className="whitespace-pre-wrap text-gray-800 leading-relaxed text-xs sm:text-sm">
                            {interpretation.interpretation_text}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
                
                {interpretation.status === 'processing' && (
                  <div className="mt-3 sm:mt-4 p-3 sm:p-4 bg-gradient-to-r from-blue-50 to-cyan-50 border border-blue-200 rounded-lg sm:rounded-xl">
                    <div className="flex items-center gap-2 sm:gap-3">
                      <Loader2 className="h-4 w-4 sm:h-5 sm:w-5 text-blue-600 animate-spin flex-shrink-0" />
                      <p className="text-xs sm:text-sm text-blue-900 font-medium">
                        ⏳ Обработка документов... <span className="hidden sm:inline">Это может занять до минуты.</span>
                      </p>
                    </div>
                  </div>
                )}
                
                {interpretation.status === 'pending' && (
                  <div className="mt-3 sm:mt-4 p-3 sm:p-4 bg-gradient-to-r from-yellow-50 to-amber-50 border border-yellow-200 rounded-lg sm:rounded-xl">
                    <div className="flex items-center gap-2 sm:gap-3">
                      <Clock className="h-4 w-4 sm:h-5 sm:w-5 text-yellow-600 flex-shrink-0" />
                      <p className="text-xs sm:text-sm text-yellow-900 font-medium">
                        ⏰ В очереди на обработку...
                      </p>
                    </div>
                  </div>
                )}
                
                {interpretation.status === 'failed' && interpretation.error_message && (
                  <div className="mt-3 sm:mt-4 p-3 sm:p-4 bg-gradient-to-r from-red-50 to-pink-50 border border-red-200 rounded-lg sm:rounded-xl">
                    <div className="flex items-start gap-2 sm:gap-3">
                      <XCircle className="h-4 w-4 sm:h-5 sm:w-5 text-red-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-xs sm:text-sm font-semibold text-red-900 mb-1">
                          ❌ Ошибка при обработке
                        </p>
                        <p className="text-xs sm:text-sm text-red-700">
                          {interpretation.error_message}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Timestamps */}
                <div className="mt-3 sm:mt-4 flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-4 text-xs text-gray-500">
                  <span>
                    Создано: {format(new Date(interpretation.created_at), 'dd.MM.yyyy HH:mm')}
                  </span>
                  {interpretation.completed_at && (
                    <span>
                      Завершено: {format(new Date(interpretation.completed_at), 'dd.MM.yyyy HH:mm')}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

