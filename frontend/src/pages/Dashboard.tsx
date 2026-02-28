import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileText, Upload, ArrowRight, BookOpen, Plus, Calendar } from 'lucide-react'
import { documentsService } from '../services/documents'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import UploadModal from '../components/Documents/UploadModal'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'

export default function Dashboard() {
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const { user } = useAuthStore()

  const { data: documents } = useQuery({
    queryKey: ['documents', 'recent'],
    queryFn: () => {
      const oneDayAgo = new Date()
      oneDayAgo.setHours(oneDayAgo.getHours() - 24)
      return documentsService.getDocuments({
        limit: 10,
        created_from: oneDayAgo.toISOString(),
        sort_by: 'created_at',
      })
    },
  })

  const getCurrentGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return '☀️ Доброе утро'
    if (hour < 18) return '🌤️ Добрый день'
    return '🌙 Добрый вечер'
  }

  const today = format(new Date(), "d MMMM, EEEE", { locale: ru })
  const firstName = user?.full_name?.split(' ')[0]

  return (
    <div className="space-y-4 page-transition">
      {/* Hero Section */}
      <div className="relative overflow-hidden medical-card-gradient rounded-2xl p-5 sm:p-8">
        <div className="relative z-10">
          <p className="text-xs font-medium text-[#4A90E2]/80 uppercase tracking-wide mb-1 capitalize">
            {today}
          </p>
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-900 mb-1">
            {getCurrentGreeting()}{firstName ? `, ${firstName}` : ''}
          </h1>
          <p className="text-sm text-gray-500 mb-5">Здоровье под контролем ✨</p>
          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="btn-primary w-full sm:w-auto justify-center"
          >
            <Upload className="h-4 w-4" />
            Загрузить документ
          </button>
        </div>
        <div className="absolute top-0 right-0 w-48 h-48 bg-white/20 rounded-full -mr-24 -mt-24 blur-3xl pointer-events-none" />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Link to="/documents" className="medical-card group cursor-pointer block">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0">
              <BookOpen className="h-6 w-6 text-[#4A90E2]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-base font-semibold text-gray-900">Медкарта</p>
              <p className="text-xs text-gray-500">Все ваши документы</p>
            </div>
            <ArrowRight className="h-5 w-5 text-gray-300 flex-shrink-0" />
          </div>
        </Link>

        <button
          onClick={() => setIsUploadModalOpen(true)}
          className="medical-card group cursor-pointer text-left w-full"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-green-100 flex items-center justify-center flex-shrink-0">
              <Plus className="h-6 w-6 text-[#7ED957]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-base font-semibold text-gray-900">Новый документ</p>
              <p className="text-xs text-gray-500">PDF, фото или скан</p>
            </div>
            <Upload className="h-5 w-5 text-gray-300 flex-shrink-0" />
          </div>
        </button>
      </div>

      {/* Recent Documents */}
      <div className="medical-card">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-semibold text-gray-900 flex items-center gap-2">
              <Calendar className="h-4 w-4 text-[#4A90E2]" />
              Последние документы
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">За последние 24 часа</p>
          </div>
          <Link
            to="/documents"
            className="text-xs font-semibold text-[#4A90E2] flex items-center gap-1"
          >
            Все
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        <div className="divide-y divide-gray-50">
          {documents && documents.length > 0 ? (
            documents.map((doc) => (
              <div key={doc.id} className="py-3 flex items-center gap-3 active:opacity-70">
                <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                  <FileText className="h-4 w-4 text-[#4A90E2]" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {doc.original_filename}
                  </p>
                  <p className="text-xs text-gray-400 truncate">
                    {doc.document_type || 'Неизвестный тип'}
                    {doc.specialty && ` · ${doc.specialty}`}
                  </p>
                </div>
                <span className={`text-xs font-semibold flex-shrink-0 ${
                  doc.processing_status === 'completed' ? 'text-green-500' :
                  doc.processing_status === 'processing' ? 'text-yellow-500' :
                  doc.processing_status === 'failed' ? 'text-red-500' : 'text-gray-300'
                }`}>
                  {doc.processing_status === 'completed' ? '✓' :
                   doc.processing_status === 'processing' ? '⏳' :
                   doc.processing_status === 'failed' ? '✗' : '·'}
                </span>
              </div>
            ))
          ) : (
            <div className="py-10 text-center">
              <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-gray-100 flex items-center justify-center">
                <FileText className="h-7 w-7 text-gray-400" />
              </div>
              <p className="text-sm font-semibold text-gray-700 mb-1">Нет документов</p>
              <p className="text-xs text-gray-400 mb-4">Загрузите первый медицинский документ</p>
              <button
                onClick={() => setIsUploadModalOpen(true)}
                className="inline-flex items-center gap-2 px-4 py-2.5 bg-[#4A90E2] text-white rounded-xl text-sm font-medium"
              >
                <Upload className="h-4 w-4" />
                Загрузить
              </button>
            </div>
          )}
        </div>
      </div>

      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
      />
    </div>
  )
}
