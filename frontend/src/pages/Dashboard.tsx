import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FileText, Upload, ArrowRight, BookOpen, Plus, Calendar } from 'lucide-react'
import { documentsService } from '../services/documents'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import UploadModal from '../components/Documents/UploadModal'
import DocumentListItem from '../components/Documents/DocumentListItem'
import DocumentModal from '../components/Documents/DocumentModal'
import RemindersCard from '../components/Reminders/RemindersCard'
import ReminderFormModal from '../components/Reminders/ReminderFormModal'
import TreatmentPlanCard from '../components/Dashboard/TreatmentPlanCard'
import type { Reminder } from '../types'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'

export default function Dashboard() {
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null)
  const [reminderForm, setReminderForm] = useState<{ open: boolean; reminder: Reminder | null }>({ open: false, reminder: null })
  const { user } = useAuthStore()
  const queryClient = useQueryClient()

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

  const deleteMutation = useMutation({
    mutationFn: documentsService.deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
  })

  const handleDownload = (docId: string, filename: string) => {
    const url = documentsService.getDocumentFileUrl(docId)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const getCurrentGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Доброе утро'
    if (hour < 18) return 'Добрый день'
    return 'Добрый вечер'
  }

  const today = format(new Date(), "d MMMM, EEEE", { locale: ru })
  const firstName = user?.full_name?.split(' ')[0]

  return (
    <div className="space-y-5">
      {/* Hero Section */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 sm:p-8">
        <p className="text-[13px] font-medium text-gray-400 uppercase tracking-wide mb-1 capitalize">
          {today}
        </p>
        <h1 className="text-[28px] sm:text-[32px] font-semibold text-gray-900 tracking-tight mb-1">
          {getCurrentGreeting()}{firstName ? `, ${firstName}` : ''}
        </h1>
        <button
          onClick={() => setIsUploadModalOpen(true)}
          className="inline-flex items-center gap-2 bg-emerald-500 text-white px-5 py-2.5 rounded-xl text-[14px] font-medium hover:bg-emerald-600 transition-colors"
        >
          <Upload className="h-4 w-4" />
          Загрузить документ
        </button>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link
          to="/documents"
          className="bg-white rounded-2xl border border-gray-100 p-5 hover:border-emerald-200 transition-colors group block"
        >
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 rounded-xl bg-emerald-50 flex items-center justify-center shrink-0">
              <BookOpen className="h-5 w-5 text-emerald-500" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[15px] font-semibold text-gray-900">Медкарта</p>
              <p className="text-[13px] text-gray-500">Все ваши документы</p>
            </div>
            <ArrowRight className="h-4 w-4 text-gray-300 group-hover:text-emerald-400 transition-colors shrink-0" />
          </div>
        </Link>

        <button
          onClick={() => setIsUploadModalOpen(true)}
          className="bg-white rounded-2xl border border-gray-100 p-5 hover:border-emerald-200 transition-colors group text-left w-full"
        >
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 rounded-xl bg-emerald-50 flex items-center justify-center shrink-0">
              <Plus className="h-5 w-5 text-emerald-500" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[15px] font-semibold text-gray-900">Новый документ</p>
              <p className="text-[13px] text-gray-500">PDF, фото или скан</p>
            </div>
            <Upload className="h-4 w-4 text-gray-300 group-hover:text-emerald-400 transition-colors shrink-0" />
          </div>
        </button>
      </div>

      {/* Treatment plan — entry point */}
      <TreatmentPlanCard />

      {/* Reminders */}
      <RemindersCard
        onAdd={() => setReminderForm({ open: true, reminder: null })}
        onOpen={(reminder) => setReminderForm({ open: true, reminder })}
        onOpenDocument={(id) => setSelectedDocumentId(id)}
      />

      {/* Recent Documents */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-[15px] font-semibold text-gray-900 flex items-center gap-2">
              <Calendar className="h-4 w-4 text-emerald-500" />
              Последние документы
            </h3>
            <p className="text-[12px] text-gray-400 mt-0.5">За последние 24 часа</p>
          </div>
          <Link
            to="/documents"
            className="text-[13px] font-medium text-emerald-600 hover:text-emerald-700 flex items-center gap-1 transition-colors"
          >
            Все
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        <div className="divide-y divide-gray-50 -mx-6">
          {documents && documents.length > 0 ? (
            documents.map((doc) => (
              <DocumentListItem
                key={doc.id}
                doc={doc}
                onClick={(id) => setSelectedDocumentId(id)}
                onDownload={(id, filename) => handleDownload(id, filename)}
                onDelete={(id) => {
                  if (window.confirm('Удалить этот документ?')) {
                    deleteMutation.mutate(id)
                  }
                }}
              />
            ))
          ) : (
            <div className="py-12 text-center">
              <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-gray-50 flex items-center justify-center">
                <FileText className="h-6 w-6 text-gray-300" />
              </div>
              <p className="text-[15px] font-medium text-gray-900 mb-1">Нет документов</p>
              <p className="text-[13px] text-gray-500 mb-5">Загрузите первый медицинский документ</p>
              <button
                onClick={() => setIsUploadModalOpen(true)}
                className="inline-flex items-center gap-2 bg-emerald-500 text-white px-5 py-2.5 rounded-xl text-[14px] font-medium hover:bg-emerald-600 transition-colors"
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

      {selectedDocumentId && (
        <DocumentModal
          documentId={selectedDocumentId}
          onClose={() => setSelectedDocumentId(null)}
        />
      )}

      <ReminderFormModal
        isOpen={reminderForm.open}
        reminder={reminderForm.reminder}
        onClose={() => setReminderForm({ open: false, reminder: null })}
        onOpenDocument={(docId) => {
          setReminderForm({ open: false, reminder: null })
          setSelectedDocumentId(docId)
        }}
      />
    </div>
  )
}
