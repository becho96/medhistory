import api from '../lib/api'
import type { Reminder, ReminderKind } from '../types'

export interface ReminderCreateInput {
  kind: ReminderKind
  title: string
  due_date?: string | null
  target_specialty?: string | null
  note?: string | null
}

export interface ReminderUpdateInput {
  kind?: ReminderKind
  title?: string
  due_date?: string | null
  target_specialty?: string | null
  note?: string | null
}

export const remindersService = {
  listReminders: async (includeResolved = false): Promise<Reminder[]> =>
    (await api.get('/reminders/', { params: { include_resolved: includeResolved } })).data,

  createReminder: async (input: ReminderCreateInput): Promise<Reminder> =>
    (await api.post('/reminders/', input)).data,

  updateReminder: async (id: string, input: ReminderUpdateInput): Promise<Reminder> =>
    (await api.patch(`/reminders/${id}`, input)).data,

  completeReminder: async (id: string): Promise<Reminder> =>
    (await api.post(`/reminders/${id}/done`)).data,

  dismissReminder: async (id: string, reason: 'not_required' | 'incorrect' = 'not_required'): Promise<Reminder> =>
    (await api.post(`/reminders/${id}/dismiss`, { reason })).data,

  deleteReminder: async (id: string): Promise<void> => {
    await api.delete(`/reminders/${id}`)
  },
}
