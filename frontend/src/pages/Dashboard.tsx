import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileText, Activity, Upload, TrendingUp, Users, Brain, Calendar, ArrowRight, Heart } from 'lucide-react'
import { documentsService } from '../services/documents'
import { timelineService } from '../services/timeline'
import { Link } from 'react-router-dom'
import UploadModal from '../components/Documents/UploadModal'

export default function Dashboard() {
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const { data: documents } = useQuery({
    queryKey: ['documents', 'recent'],
    queryFn: () => {
      const oneDayAgo = new Date()
      oneDayAgo.setHours(oneDayAgo.getHours() - 24)
      
      return documentsService.getDocuments({ 
        limit: 10,
        created_from: oneDayAgo.toISOString(),
        sort_by: 'created_at'
      })
    },
  })

  const { data: stats } = useQuery({
    queryKey: ['timeline-stats'],
    queryFn: timelineService.getTimelineStats,
  })

  const getCurrentGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return '☀️ Доброе утро'
    if (hour < 18) return '🌤️ Добрый день'
    return '🌙 Добрый вечер'
  }

  return (
    <div className="space-y-4 md:space-y-8 page-transition">
      {/* Hero Section with Greeting */}
      <div className="relative overflow-hidden medical-card-gradient rounded-2xl md:rounded-3xl p-4 sm:p-6 md:p-8">
        <div className="relative z-10">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-900 mb-1 md:mb-2">
                {getCurrentGreeting()}
              </h1>
              <p className="text-sm sm:text-base md:text-lg text-gray-600 mb-4 md:mb-6">
                Добро пожаловать в вашу медицинскую историю. Здоровье под контролем ✨
              </p>
              <button
                onClick={() => setIsUploadModalOpen(true)}
                className="btn-primary text-sm sm:text-base w-full sm:w-auto"
              >
                <Upload className="h-4 w-4 sm:h-5 sm:w-5" />
                <span className="hidden sm:inline">Загрузить медицинские документы</span>
                <span className="sm:hidden">Загрузить документы</span>
              </button>
            </div>
            <div className="hidden lg:block">
              <div className="w-32 h-32 bg-white/50 rounded-full flex items-center justify-center backdrop-blur-sm">
                <Heart className="h-16 w-16 text-[#4A90E2]" />
              </div>
            </div>
          </div>
        </div>
        {/* Decorative elements */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/20 rounded-full -mr-32 -mt-32 blur-3xl"></div>
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-[#4A90E2]/10 rounded-full -ml-24 -mb-24 blur-2xl"></div>
      </div>

      {/* Key Metrics - Modern Card Design */}
      <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 md:gap-6">
        {/* Total Documents */}
        <div className="medical-card group cursor-pointer">
          <div className="flex items-start justify-between mb-2 sm:mb-4">
            <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg sm:rounded-xl bg-blue-100 flex items-center justify-center group-hover:scale-110 transition-transform">
              <FileText className="h-5 w-5 sm:h-6 sm:w-6 text-[#4A90E2]" />
            </div>
            <div className="hidden sm:flex items-center gap-1 text-xs font-medium text-green-600">
              <TrendingUp className="h-3 w-3" />
              +12%
            </div>
          </div>
          <div className="space-y-0.5 sm:space-y-1">
            <p className="text-xs sm:text-sm font-medium text-gray-500">Всего документов</p>
            <p className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900">{stats?.total_documents || 0}</p>
          </div>
        </div>

        {/* Specialties */}
        <div className="medical-card group cursor-pointer">
          <div className="flex items-start justify-between mb-2 sm:mb-4">
            <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg sm:rounded-xl bg-green-100 flex items-center justify-center group-hover:scale-110 transition-transform">
              <Users className="h-5 w-5 sm:h-6 sm:w-6 text-[#7ED957]" />
            </div>
            <div className="hidden sm:flex items-center gap-1 text-xs font-medium text-gray-400">
              <Activity className="h-3 w-3" />
            </div>
          </div>
          <div className="space-y-0.5 sm:space-y-1">
            <p className="text-xs sm:text-sm font-medium text-gray-500">Специализаций</p>
            <p className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900">
              {stats?.by_specialty ? Object.keys(stats.by_specialty).length : 0}
            </p>
          </div>
        </div>

        {/* Document Types */}
        <div className="medical-card group cursor-pointer">
          <div className="flex items-start justify-between mb-2 sm:mb-4">
            <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg sm:rounded-xl bg-purple-100 flex items-center justify-center group-hover:scale-110 transition-transform">
              <Activity className="h-5 w-5 sm:h-6 sm:w-6 text-purple-600" />
            </div>
          </div>
          <div className="space-y-0.5 sm:space-y-1">
            <p className="text-xs sm:text-sm font-medium text-gray-500">Типов документов</p>
            <p className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900">
              {stats?.by_type ? Object.keys(stats.by_type).length : 0}
            </p>
          </div>
        </div>

        {/* AI Insights */}
        <Link to="/interpretations" className="medical-card group cursor-pointer block">
          <div className="flex items-start justify-between mb-2 sm:mb-4">
            <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg sm:rounded-xl bg-indigo-100 flex items-center justify-center group-hover:scale-110 transition-transform">
              <Brain className="h-5 w-5 sm:h-6 sm:w-6 text-indigo-600" />
            </div>
            <div className="flex items-center gap-1 text-xs font-medium text-indigo-600">
              <ArrowRight className="h-3 w-3 sm:h-4 sm:w-4" />
            </div>
          </div>
          <div className="space-y-0.5 sm:space-y-1">
            <p className="text-xs sm:text-sm font-medium text-gray-500">AI Интерпретации</p>
            <p className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900">Доступно</p>
          </div>
        </Link>
      </div>

      {/* Recent Documents - Full Width */}
      <div className="medical-card">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 sm:mb-6 gap-2">
          <div>
            <h3 className="text-lg sm:text-xl font-semibold text-gray-900 flex items-center gap-2">
              <Calendar className="h-4 w-4 sm:h-5 sm:w-5 text-[#4A90E2]" />
              Последние документы
            </h3>
            <p className="text-xs sm:text-sm text-gray-500 mt-1">Загружено за последние 24 часа</p>
          </div>
          <Link
            to="/documents"
            className="text-xs sm:text-sm font-semibold text-[#4A90E2] hover:text-[#3A7BC8] flex items-center gap-1 group w-fit"
          >
            Все документы
            <ArrowRight className="h-3 w-3 sm:h-4 sm:w-4 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>

        <div className="space-y-2 sm:space-y-3">
          {documents && documents.length > 0 ? (
            documents.map((doc, index) => (
              <div
                key={doc.id}
                className="p-3 sm:p-4 rounded-lg sm:rounded-xl bg-gray-50 hover:bg-gray-100 transition-all cursor-pointer border border-transparent hover:border-[#4A90E2]/20"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <div className="flex items-start sm:items-center gap-2 sm:gap-3">
                  <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-white flex items-center justify-center flex-shrink-0">
                    <FileText className="h-4 w-4 sm:h-5 sm:w-5 text-[#4A90E2]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs sm:text-sm font-semibold text-gray-900 truncate">
                      {doc.original_filename}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5 truncate">
                      {doc.document_type || 'Неизвестный тип'} {doc.specialty && `• ${doc.specialty}`}
                    </p>
                  </div>
                  <div className="flex-shrink-0">
                    <span
                      className={`inline-flex items-center px-2 sm:px-3 py-1 rounded-full text-xs font-semibold ${
                        doc.processing_status === 'completed'
                          ? 'bg-green-100 text-green-700'
                          : doc.processing_status === 'processing'
                          ? 'bg-yellow-100 text-yellow-700'
                          : doc.processing_status === 'failed'
                          ? 'bg-red-100 text-red-700'
                          : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      <span className="hidden sm:inline">
                        {doc.processing_status === 'completed'
                          ? '✓ Обработан'
                          : doc.processing_status === 'processing'
                          ? '⏳ Обработка'
                          : doc.processing_status === 'failed'
                          ? '✗ Ошибка'
                          : '⋯ Ожидание'}
                      </span>
                      <span className="sm:hidden">
                        {doc.processing_status === 'completed'
                          ? '✓'
                          : doc.processing_status === 'processing'
                          ? '⏳'
                          : doc.processing_status === 'failed'
                          ? '✗'
                          : '⋯'}
                      </span>
                    </span>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="py-8 sm:py-12 text-center">
              <div className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4 rounded-full bg-gray-100 flex items-center justify-center">
                <FileText className="h-6 w-6 sm:h-8 sm:w-8 text-gray-400" />
              </div>
              <h3 className="text-sm sm:text-base font-semibold text-gray-900 mb-2">Нет документов</h3>
              <p className="text-xs sm:text-sm text-gray-500 mb-4 sm:mb-6 px-4">
                Начните с загрузки вашего первого медицинского документа
              </p>
              <button
                onClick={() => setIsUploadModalOpen(true)}
                className="inline-flex items-center px-4 py-2 bg-[#4A90E2] text-white rounded-lg hover:bg-[#3A7BC8] transition-colors font-medium text-xs sm:text-sm"
              >
                <Upload className="h-4 w-4 mr-2" />
                Загрузить документ
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
      />
    </div>
  )
}

