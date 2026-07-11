import { useState, useEffect } from 'react'
import { X, Trash2, FileText, Stethoscope, Check, Calendar } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { remindersService } from '../../services/reminders'
import type { Reminder, ReminderKind } from '../../types'

interface ReminderFormModalProps {
  isOpen: boolean
  onClose: () => void
  reminder?: Reminder | null
  onOpenDocument?: (documentId: string) => void
}

const KIND_OPTIONS: Array<{ value: ReminderKind; label: string }> = [
  { value: 'follow_up_appointment', label: 'Повторный приём' },
  { value: 'referral_specialist', label: 'Консультация специалиста' },
  { value: 'referral_research', label: 'Направление на исследование' },
]

export default function ReminderFormModal({ isOpen, onClose, reminder, onOpenDocument }: ReminderFormModalProps) {
  const isEdit = Boolean(reminder)
  const isAuto = Boolean(reminder?.source_document_id)
  const queryClient = useQueryClient()

  const [kind, setKind] = useState<ReminderKind>('follow_up_appointment')
  const [title, setTitle] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [specialty, setSpecialty] = useState('')
  const [note, setNote] = useState('')

  useEffect(() => {
    if (reminder) {
      setKind(reminder.kind)
      setTitle(reminder.title)
      setDueDate(reminder.due_date ? reminder.due_date.slice(0, 10) : '')
      setSpecialty(reminder.target_specialty || '')
      setNote(reminder.note || '')
    } else {
      setKind('follow_up_appointment')
      setTitle('')
      setDueDate('')
      setSpecialty('')
      setNote('')
    }
  }, [reminder, isOpen])

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['reminders'] })

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload = {
        kind,
        title: title.trim(),
        due_date: dueDate || null,
        target_specialty: specialty.trim() || null,
        note: note.trim() || null,
      }
      return reminder
        ? remindersService.updateReminder(reminder.id, payload)
        : remindersService.createReminder(payload)
    },
    onSuccess: () => {
      invalidate()
      toast.success(isEdit ? 'Напоминание обновлено' : 'Напоминание добавлено')
      onClose()
    },
    onError: (error: { response?: { data?: { detail?: string } } }) =>
      toast.error(error.response?.data?.detail || 'Не удалось сохранить'),
  })

  const completeMutation = useMutation({
    mutationFn: () => remindersService.completeReminder(reminder!.id),
    onSuccess: () => { invalidate(); toast.success('Отметили как выполнено'); onClose() },
    onError: () => toast.error('Не удалось обновить'),
  })

  const deleteMutation = useMutation({
    mutationFn: () => remindersService.deleteReminder(reminder!.id),
    onSuccess: () => { invalidate(); toast.success('Убрали из напоминаний'); onClose() },
    onError: () => toast.error('Не удалось удалить'),
  })

  if (!isOpen) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) {
      toast.error('Укажите название напоминания')
      return
    }
    saveMutation.mutate()
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-900">
            {isEdit ? 'Напоминание' : 'Новое напоминание'}
          </h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {/* Источник: назначено после приёма */}
          {isAuto && (
            <div className="rounded-lg bg-emerald-50 border border-emerald-100 p-3.5">
              <p className="text-[13px] text-emerald-800 flex items-center gap-1.5">
                <Stethoscope className="h-4 w-4 shrink-0" />
                {reminder?.source_specialty
                  ? `Назначено после приёма — ${reminder.source_specialty}${reminder.source_doctor_name ? `, ${reminder.source_doctor_name}` : ''}`
                  : 'Назначено после приёма врача'}
              </p>
              {reminder?.source_document_date && (
                <p className="mt-1.5 text-[12.5px] text-emerald-700 flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5 shrink-0" />
                  Направление от {format(parseISO(reminder.source_document_date), 'd MMMM yyyy', { locale: ru })}
                </p>
              )}
              {reminder?.source_document_id && onOpenDocument && (
                <button
                  type="button"
                  onClick={() => onOpenDocument(reminder.source_document_id!)}
                  className="mt-2 text-[13px] font-medium text-emerald-700 hover:text-emerald-800 inline-flex items-center gap-1.5"
                >
                  <FileText className="h-3.5 w-3.5" />
                  {reminder.source_document_title || 'Открыть документ-источник'}
                </button>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Тип</label>
              <select
                value={kind}
                onChange={(e) => setKind(e.target.value as ReminderKind)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm"
              >
                {KIND_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Название *</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Напр. Повторный приём кардиолога"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Запланировано на</label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm"
              />
              <p className="text-xs text-gray-400 mt-1">
                Если врач назвал срок, дата подставлена автоматически. Укажите, на какое число вы записались.
              </p>
            </div>

            {!isAuto && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Специальность</label>
                <input
                  type="text"
                  value={specialty}
                  onChange={(e) => setSpecialty(e.target.value)}
                  placeholder="Напр. Кардиология"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm"
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Заметка</label>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm resize-none"
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              {isEdit ? (
                <button
                  type="button"
                  onClick={() => deleteMutation.mutate()}
                  className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-red-600 transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                  Убрать
                </button>
              ) : <span />}
              <div className="flex items-center gap-2">
                {isEdit && (
                  <button
                    type="button"
                    onClick={() => completeMutation.mutate()}
                    className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-emerald-700 bg-emerald-50 rounded-lg hover:bg-emerald-100 transition-colors"
                  >
                    <Check className="h-4 w-4" />
                    Выполнено
                  </button>
                )}
                <button
                  type="submit"
                  disabled={saveMutation.isPending}
                  className="px-4 py-2 bg-emerald-500 text-white text-sm font-medium rounded-lg hover:bg-emerald-600 transition-colors disabled:opacity-60"
                >
                  {isEdit ? 'Сохранить' : 'Добавить'}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
