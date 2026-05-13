import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, X, Trash2, PauseCircle, PlayCircle, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { adminService } from '../../services/admin'
import type { PromoCodeCreate } from '../../types'

const DURATION_PRESETS = [
  { value: 30, label: '30 дней' },
  { value: 90, label: '90 дней' },
  { value: 365, label: '1 год' },
]

function formatDate(iso?: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function Promocodes() {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<PromoCodeCreate>({
    code: '',
    duration_days: 30,
    max_activations: 1,
    expires_at: null,
    comment: '',
  })

  const { data: promocodes, isLoading } = useQuery({
    queryKey: ['admin', 'promocodes'],
    queryFn: () => adminService.listPromocodes({ limit: 200 }),
  })

  const createMutation = useMutation({
    mutationFn: adminService.createPromocode,
    onSuccess: (created) => {
      toast.success(`Создан промокод ${created.code}`)
      setShowCreate(false)
      setForm({ code: '', duration_days: 30, max_activations: 1, expires_at: null, comment: '' })
      queryClient.invalidateQueries({ queryKey: ['admin', 'promocodes'] })
      queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] })
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail
      const code = typeof detail === 'object' && detail !== null ? detail.code : null
      if (code === 'duplicate_code') {
        toast.error('Такой код уже существует')
      } else {
        toast.error('Не удалось создать промокод')
      }
    },
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      adminService.updatePromocode(id, { is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'promocodes'] })
      queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminService.deletePromocode(id),
    onSuccess: () => {
      toast.success('Промокод удалён')
      queryClient.invalidateQueries({ queryKey: ['admin', 'promocodes'] })
      queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] })
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail
      const code = typeof detail === 'object' && detail !== null ? detail.code : null
      if (code === 'promo_has_activations') {
        toast.error('Нельзя удалить промокод с активациями. Деактивируйте его.')
      } else {
        toast.error('Не удалось удалить промокод')
      }
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({
      ...form,
      code: form.code?.trim() || undefined,
      comment: form.comment?.trim() || undefined,
      expires_at: form.expires_at || null,
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Промокоды</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium"
        >
          <Plus className="w-4 h-4" /> Новый промокод
        </button>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500">
            <tr>
              <th className="text-left px-4 py-3 font-medium">Код</th>
              <th className="text-left px-4 py-3 font-medium">Срок Pro</th>
              <th className="text-left px-4 py-3 font-medium">Активаций</th>
              <th className="text-left px-4 py-3 font-medium">Истекает</th>
              <th className="text-left px-4 py-3 font-medium">Статус</th>
              <th className="text-left px-4 py-3 font-medium">Комментарий</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={7} className="text-center py-8 text-gray-400">Загрузка…</td>
              </tr>
            )}
            {!isLoading && promocodes && promocodes.length === 0 && (
              <tr>
                <td colSpan={7} className="text-center py-8 text-gray-400">Промокодов пока нет</td>
              </tr>
            )}
            {promocodes?.map((p) => (
              <tr key={p.id} className="border-t border-gray-100">
                <td className="px-4 py-3 font-mono text-gray-900">{p.code}</td>
                <td className="px-4 py-3 text-gray-700">{p.duration_days} дн.</td>
                <td className="px-4 py-3 text-gray-700">
                  {p.activations_count}/{p.max_activations}
                </td>
                <td className="px-4 py-3 text-gray-700">{formatDate(p.expires_at)}</td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                      p.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500'
                    }`}
                  >
                    {p.is_active ? 'Активен' : 'Деактивирован'}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500 max-w-xs truncate" title={p.comment ?? ''}>
                  {p.comment || '—'}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="inline-flex items-center gap-2">
                    <button
                      onClick={() => toggleMutation.mutate({ id: p.id, is_active: !p.is_active })}
                      title={p.is_active ? 'Деактивировать' : 'Активировать'}
                      className="p-1.5 rounded hover:bg-gray-100 text-gray-500"
                    >
                      {p.is_active ? (
                        <PauseCircle className="w-4 h-4" />
                      ) : (
                        <PlayCircle className="w-4 h-4" />
                      )}
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(`Удалить промокод ${p.code}?`)) deleteMutation.mutate(p.id)
                      }}
                      disabled={p.activations_count > 0}
                      title={p.activations_count > 0 ? 'Есть активации — удалить нельзя' : 'Удалить'}
                      className="p-1.5 rounded hover:bg-red-50 text-red-600 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <div className="fixed inset-0 z-[110] flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h3 className="text-base font-semibold text-gray-900">Новый промокод</h3>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Код</label>
                <input
                  type="text"
                  value={form.code ?? ''}
                  onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                  placeholder="Оставьте пустым для генерации"
                  maxLength={64}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Срок Pro (дней)</label>
                <div className="flex gap-2 mb-2">
                  {DURATION_PRESETS.map((preset) => (
                    <button
                      key={preset.value}
                      type="button"
                      onClick={() => setForm({ ...form, duration_days: preset.value })}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium ${
                        form.duration_days === preset.value
                          ? 'bg-emerald-500 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
                <input
                  type="number"
                  min={1}
                  max={3650}
                  value={form.duration_days}
                  onChange={(e) => setForm({ ...form, duration_days: parseInt(e.target.value, 10) || 1 })}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Максимум активаций
                </label>
                <input
                  type="number"
                  min={1}
                  value={form.max_activations}
                  onChange={(e) => setForm({ ...form, max_activations: parseInt(e.target.value, 10) || 1 })}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
                <p className="text-xs text-gray-500 mt-1">1 — одноразовый промокод</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Действителен до (опционально)
                </label>
                <input
                  type="datetime-local"
                  value={form.expires_at ? form.expires_at.slice(0, 16) : ''}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      expires_at: e.target.value ? new Date(e.target.value).toISOString() : null,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Комментарий</label>
                <input
                  type="text"
                  value={form.comment ?? ''}
                  onChange={(e) => setForm({ ...form, comment: e.target.value })}
                  placeholder="Например, EarlyBird campaign"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-sm font-medium text-gray-700"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium flex items-center gap-2 disabled:opacity-50"
                >
                  {createMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  Создать
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
