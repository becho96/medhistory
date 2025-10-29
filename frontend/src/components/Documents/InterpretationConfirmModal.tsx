import { X, AlertCircle, Brain, Loader2 } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { interpretationsService } from '../../services/interpretations'
import { useNavigate } from 'react-router-dom'

interface InterpretationConfirmModalProps {
  isOpen: boolean
  onClose: () => void
  selectedDocuments: Array<{
    id: string
    original_filename: string
    document_date?: string
    document_type?: string
  }>
}

export default function InterpretationConfirmModal({
  isOpen,
  onClose,
  selectedDocuments
}: InterpretationConfirmModalProps) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  
  const createInterpretationMutation = useMutation({
    mutationFn: (documentIds: string[]) => 
      interpretationsService.createInterpretation({ document_ids: documentIds }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['interpretations'] })
      toast.success('Интерпретация создана! Обработка началась.')
      onClose()
      // Navigate to interpretations page
      navigate('/interpretations')
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || 'Не удалось создать интерпретацию'
      toast.error(errorMessage)
    }
  })
  
  const handleSubmit = () => {
    const documentIds = selectedDocuments.map(doc => doc.id)
    createInterpretationMutation.mutate(documentIds)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        {/* Backdrop */}
        <div 
          className="fixed inset-0 bg-black/50 transition-opacity"
          onClick={onClose}
        />
        
        {/* Modal */}
        <div className="relative w-full max-w-2xl bg-white rounded-lg shadow-xl">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-purple-100">
                <Brain className="h-6 w-6 text-purple-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">
                Отправить на AI-интерпретацию
              </h3>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
          
          {/* Body */}
          <div className="p-6 space-y-4">
            {/* Disclaimer */}
            <div className="flex gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg">
              <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-amber-800">
                <p className="font-semibold mb-1">Важное предупреждение</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>AI-интерпретация носит информационный характер и НЕ заменяет консультацию врача</li>
                  <li>Результаты не являются медицинским диагнозом</li>
                  <li>Обязательно обсудите результаты с лечащим врачом</li>
                </ul>
              </div>
            </div>
            
            {/* Selected documents */}
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-2">
                Выбранные документы ({selectedDocuments.length}):
              </h4>
              <div className="max-h-60 overflow-y-auto border border-gray-200 rounded-lg">
                <ul className="divide-y divide-gray-200">
                  {selectedDocuments.map((doc) => (
                    <li key={doc.id} className="p-3 hover:bg-gray-50">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {doc.original_filename}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            {doc.document_type && (
                              <span className="text-xs text-gray-500">
                                {doc.document_type}
                              </span>
                            )}
                            {doc.document_date && (
                              <span className="text-xs text-gray-500">
                                • {new Date(doc.document_date).toLocaleDateString('ru-RU')}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            
            {/* Additional info */}
            <div className="text-sm text-gray-600 bg-gray-50 p-4 rounded-lg">
              <p>
                <strong>Что будет происходить:</strong>
              </p>
              <ol className="list-decimal list-inside mt-2 space-y-1">
                <li>AI проанализирует все выбранные документы</li>
                <li>Будут учтены результаты анализов и их динамика во времени</li>
                <li>Вы получите интерпретацию с объяснением показателей</li>
                <li>Процесс займет около 30-60 секунд</li>
              </ol>
            </div>
          </div>
          
          {/* Footer */}
          <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
            <button
              onClick={onClose}
              disabled={createInterpretationMutation.isPending}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
            >
              Отмена
            </button>
            <button
              onClick={handleSubmit}
              disabled={createInterpretationMutation.isPending}
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-purple-600 border border-transparent rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50"
            >
              {createInterpretationMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Отправка...
                </>
              ) : (
                <>
                  <Brain className="h-4 w-4 mr-2" />
                  Отправить на интерпретацию
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

