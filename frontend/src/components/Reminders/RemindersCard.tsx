import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { BellRing, Plus, Check, X, Stethoscope, FlaskConical, ChevronRight } from 'lucide-react'
import { toast } from 'sonner'
import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { remindersService } from '../../services/reminders'
import type { Reminder, ReminderKind, ReminderUrgency } from '../../types'

interface RemindersCardProps {
  onAdd: () => void
  onOpen: (reminder: Reminder) => void
}

const URGENCY_STYLE: Record<ReminderUrgency, { badge: string; badgeClass: string; dot: string }> = {
  overdue: { badge: 'Просрочено', badgeClass: 'bg-red-100 text-red-700', dot: 'bg-red-500' },
  urgent: { badge: 'Скоро', badgeClass: 'bg-amber-100 text-amber-700', dot: 'bg-amber-500' },
  soon: { badge: 'На горизонте', badgeClass: 'bg-amber-50 text-amber-600', dot: 'bg-amber-400' },
  planned: { badge: 'Запланировано', badgeClass: 'bg-emerald-50 text-emerald-600', dot: 'bg-emerald-400' },
  no_date: { badge: '', badgeClass: '', dot: 'bg-gray-300' },
}

const KIND_META: Record<ReminderKind, { label: string; Icon: typeof Stethoscope }> = {
  follow_up_appointment: { label: 'Повторный приём', Icon: Stethoscope },
  referral_specialist: { label: 'Консультация специалиста', Icon: Stethoscope },
  referral_research: { label: 'Направление на исследование', Icon: FlaskConical },
}

const formatDate = (value?: string | null) =>
  value ? format(parseISO(value), 'd MMMM yyyy', { locale: ru }) : ''

const dueText = (r: Reminder): string | null => {
  switch (r.urgency_level) {
    case 'overdue':
      return `Срок был ${formatDate(r.due_date)}. Если ещё актуально — стоит запланировать`
    case 'urgent':
      return `Осталось ${r.days_left} дн. — удобное время записаться`
    case 'soon':
      return `Примерно через ${r.days_left} дн.`
    case 'planned':
      return `Запланировано на ${formatDate(r.due_date)}`
    default:
      return null
  }
}

// Плашка «кто направил»: специализация приёма + ФИО врача, иначе тип напоминания.
function ReferrerChip({ reminder }: { reminder: Reminder }) {
  const kind = KIND_META[reminder.kind] ?? KIND_META.referral_research
  const specialty = reminder.source_specialty || reminder.target_specialty
  const doctor = reminder.source_doctor_name

  if (specialty) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-[12px] text-slate-700">
        <Stethoscope className="h-3.5 w-3.5 text-slate-500 shrink-0" />
        <span className="font-semibold">{specialty}</span>
        {doctor && (
          <>
            <span className="text-slate-300">·</span>
            <span>{doctor}</span>
          </>
        )}
      </span>
    )
  }

  const KindIcon = kind.Icon
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-[12px] text-slate-700">
      <KindIcon className="h-3.5 w-3.5 text-slate-500 shrink-0" />
      <span className="font-medium">{kind.label}</span>
    </span>
  )
}

export default function RemindersCard({ onAdd, onOpen }: RemindersCardProps) {
  const queryClient = useQueryClient()

  const { data: reminders } = useQuery({
    queryKey: ['reminders'],
    queryFn: () => remindersService.listReminders(),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['reminders'] })

  const completeMutation = useMutation({
    mutationFn: (id: string) => remindersService.completeReminder(id),
    onSuccess: () => { invalidate(); toast.success('Отметили как выполнено') },
    onError: () => toast.error('Не удалось обновить напоминание'),
  })
  const dismissMutation = useMutation({
    mutationFn: (id: string) => remindersService.dismissReminder(id, 'not_required'),
    onSuccess: () => { invalidate(); toast.success('Убрали из напоминаний') },
    onError: () => toast.error('Не удалось убрать напоминание'),
  })

  const stop = (e: React.MouseEvent) => e.stopPropagation()
  const items = reminders ?? []

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="text-[15px] font-semibold text-gray-900 flex items-center gap-2">
            <BellRing className="h-4 w-4 text-emerald-500" />
            Напоминания
          </h3>
          <p className="text-[12px] text-gray-400 mt-0.5">Что назначил врач после приёма</p>
        </div>
        <button
          onClick={onAdd}
          className="text-[13px] font-medium text-emerald-600 hover:text-emerald-700 flex items-center gap-1 transition-colors"
        >
          <Plus className="h-3.5 w-3.5" />
          Добавить
        </button>
      </div>

      {items.length > 0 ? (
        <div className="space-y-2.5">
          {items.map((r) => {
            const urgency = URGENCY_STYLE[r.urgency_level]
            const due = dueText(r)
            return (
              <div
                key={r.id}
                role="button"
                tabIndex={0}
                onClick={() => onOpen(r)}
                onKeyDown={(e) => { if (e.key === 'Enter') onOpen(r) }}
                className="flex items-center gap-3 rounded-xl border border-gray-100 p-3.5 cursor-pointer hover:border-emerald-200 hover:bg-emerald-50/40 transition-colors"
              >
                <span className={`h-2 w-2 rounded-full shrink-0 ${urgency.dot}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[14px] font-medium text-gray-900">{r.title}</span>
                    {urgency.badge && (
                      <span className={`text-[11px] px-1.5 py-0.5 rounded-md font-medium ${urgency.badgeClass}`}>
                        {urgency.badge}
                      </span>
                    )}
                  </div>
                  <div className="mt-1.5">
                    <ReferrerChip reminder={r} />
                  </div>
                  {due && <p className="text-[12.5px] text-gray-600 mt-1.5">{due}</p>}
                </div>
                <div className="flex items-center gap-1 shrink-0" onClick={stop}>
                  <button
                    title="Выполнено"
                    onClick={(e) => { stop(e); completeMutation.mutate(r.id) }}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 transition-colors"
                  >
                    <Check className="h-4 w-4" />
                  </button>
                  <button
                    title="Не требуется"
                    onClick={(e) => { stop(e); dismissMutation.mutate(r.id) }}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
                  >
                    <X className="h-4 w-4" />
                  </button>
                  <ChevronRight className="h-4 w-4 text-gray-300" />
                </div>
              </div>
            )
          })}
          <p className="text-[11px] text-gray-400 pt-1.5">
            Это не медицинские рекомендации — ориентируйтесь на назначения вашего врача
          </p>
        </div>
      ) : (
        <div className="py-8 text-center">
          <div className="w-11 h-11 mx-auto mb-3 rounded-xl bg-gray-50 flex items-center justify-center">
            <BellRing className="h-5 w-5 text-gray-300" />
          </div>
          <p className="text-[14px] font-medium text-gray-900 mb-0.5">Пока нет активных напоминаний</p>
          <p className="text-[12.5px] text-gray-500">Мы подскажем, когда врач что-то назначит</p>
        </div>
      )}
    </div>
  )
}
