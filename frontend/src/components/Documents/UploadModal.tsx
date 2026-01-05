import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useQueryClient } from '@tanstack/react-query'
import { Upload, CheckCircle2, XCircle, Loader2, FileText, X } from 'lucide-react'
import { toast } from 'sonner'
import { documentsService } from '../../services/documents'

interface UploadingFile {
  id: string
  file: File
  status: 'uploading' | 'success' | 'error'
  progress: number
  error?: string
}

interface UploadModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function UploadModal({ isOpen, onClose }: UploadModalProps) {
  const queryClient = useQueryClient()
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([])

  const uploadFile = async (file: File) => {
    const fileId = `${file.name}-${Date.now()}`
    
    // Добавляем файл в список загружаемых
    setUploadingFiles((prev) => [
      ...prev,
      {
        id: fileId,
        file,
        status: 'uploading',
        progress: 0,
      },
    ])

    try {
      // Симулируем прогресс загрузки
      const progressInterval = setInterval(() => {
        setUploadingFiles((prev) =>
          prev.map((f) =>
            f.id === fileId && f.progress < 90
              ? { ...f, progress: f.progress + 10 }
              : f
          )
        )
      }, 200)

      await documentsService.uploadDocument(file)
      
      clearInterval(progressInterval)

      // Обновляем статус на успешный
      setUploadingFiles((prev) =>
        prev.map((f) =>
          f.id === fileId
            ? { ...f, status: 'success', progress: 100 }
            : f
        )
      )

      queryClient.invalidateQueries({ queryKey: ['documents'] })
      queryClient.invalidateQueries({ queryKey: ['documents-count'] })
      queryClient.invalidateQueries({ queryKey: ['documents-all'] })
      
      // Удаляем файл из списка через 3 секунды
      setTimeout(() => {
        setUploadingFiles((prev) => prev.filter((f) => f.id !== fileId))
      }, 3000)
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Ошибка загрузки'
      
      setUploadingFiles((prev) =>
        prev.map((f) =>
          f.id === fileId
            ? {
                ...f,
                status: 'error',
                error: errorMessage,
              }
            : f
        )
      )
      
      // Показываем детальное сообщение в toast
      if (errorMessage.includes('уже был загружен')) {
        toast.error(`Дубликат файла: ${file.name}`, {
          description: errorMessage,
          duration: 5000,
        })
      } else {
        toast.error(`Ошибка загрузки: ${file.name}`, {
          description: errorMessage,
        })
      }
    }
  }

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      // Загружаем все файлы параллельно
      acceptedFiles.forEach((file) => {
        uploadFile(file)
      })
      
      if (acceptedFiles.length > 0) {
        toast.success(`Начата загрузка ${acceptedFiles.length} файл(ов)`)
      }
    },
    []
  )

  const removeFile = (fileId: string) => {
    setUploadingFiles((prev) => prev.filter((f) => f.id !== fileId))
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.jpg', '.jpeg', '.png'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        ['.docx'],
    },
    maxSize: 20 * 1024 * 1024, // 20MB
    multiple: true,
  })

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const handleClose = () => {
    // Не закрываем модальное окно, если есть загружаемые файлы
    const hasUploading = uploadingFiles.some(f => f.status === 'uploading')
    if (hasUploading) {
      toast.warning('Дождитесь завершения загрузки файлов')
      return
    }
    
    // Очищаем список файлов при закрытии
    setUploadingFiles([])
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            Загрузка документов
          </h3>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1">
          <div className="space-y-4">
            {/* Drop Zone */}
            <div
              {...getRootProps()}
              className={`
                border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                transition-colors duration-200
                ${
                  isDragActive
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-300 hover:border-gray-400'
                }
              `}
            >
              <input {...getInputProps()} />
              <Upload className="mx-auto h-10 w-10 text-gray-400" />
              {isDragActive ? (
                <p className="mt-2 text-sm text-primary-600">Отпустите файлы здесь...</p>
              ) : (
                <div className="mt-2">
                  <p className="text-base text-gray-900">Перетащите файлы сюда</p>
                  <p className="text-sm text-gray-500 mt-1">
                    или нажмите для выбора файлов
                  </p>
                  <p className="text-xs text-gray-400 mt-2">
                    Поддерживаемые форматы: PDF, JPG, PNG, DOCX (макс. 20 МБ)
                  </p>
                </div>
              )}
            </div>

            {/* Список загружаемых файлов */}
            {uploadingFiles.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-gray-700">
                  Файлы ({uploadingFiles.length})
                </h4>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {uploadingFiles.map((uploadingFile) => (
                    <div
                      key={uploadingFile.id}
                      className="bg-gray-50 border border-gray-200 rounded-lg p-3"
                    >
                      <div className="flex items-start gap-3">
                        {/* Иконка файла */}
                        <div className="flex-shrink-0">
                          <FileText className="h-6 w-6 text-gray-400" />
                        </div>

                        {/* Информация о файле */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-medium text-gray-900 truncate">
                              {uploadingFile.file.name}
                            </p>
                            <button
                              onClick={() => removeFile(uploadingFile.id)}
                              className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
                              disabled={uploadingFile.status === 'uploading'}
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                          
                          <p className="text-xs text-gray-500 mt-1">
                            {formatFileSize(uploadingFile.file.size)}
                          </p>

                          {/* Прогресс-бар */}
                          {uploadingFile.status === 'uploading' && (
                            <div className="mt-2">
                              <div className="flex items-center gap-2">
                                <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                                  <div
                                    className="bg-primary-600 h-1.5 rounded-full transition-all duration-300"
                                    style={{ width: `${uploadingFile.progress}%` }}
                                  />
                                </div>
                                <span className="text-xs text-gray-600 font-medium">
                                  {uploadingFile.progress}%
                                </span>
                              </div>
                            </div>
                          )}

                          {/* Статус */}
                          <div className="flex items-center gap-2 mt-2">
                            {uploadingFile.status === 'uploading' && (
                              <>
                                <Loader2 className="h-3.5 w-3.5 text-primary-600 animate-spin" />
                                <span className="text-xs text-primary-600">
                                  Загрузка...
                                </span>
                              </>
                            )}
                            {uploadingFile.status === 'success' && (
                              <>
                                <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
                                <span className="text-xs text-green-600">
                                  Успешно загружено
                                </span>
                              </>
                            )}
                            {uploadingFile.status === 'error' && (
                              <>
                                <XCircle className="h-3.5 w-3.5 text-red-600" />
                                <span className="text-xs text-red-600">
                                  {uploadingFile.error || 'Ошибка загрузки'}
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end">
          <button
            onClick={handleClose}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-md text-sm font-medium text-gray-700 transition-colors"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  )
}

