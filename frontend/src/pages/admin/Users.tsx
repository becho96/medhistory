import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Search, Crown, Shield, ShieldOff, MinusCircle, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { adminService, type ListUsersParams } from '../../services/admin'

function formatDate(iso?: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function AdminUsers() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [tier, setTier] = useState<'all' | 'free' | 'pro'>('all')

  const params: ListUsersParams = {
    limit: 100,
    search: search.trim() || undefined,
    tier: tier === 'all' ? undefined : tier,
  }
  const { data: users, isLoading } = useQuery({
    queryKey: ['admin', 'users', params],
    queryFn: () => adminService.listUsers(params),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] })
  }

  const grantMutation = useMutation({
    mutationFn: ({ userId, days }: { userId: string; days: number }) =>
      adminService.grantPro(userId, days),
    onSuccess: () => {
      toast.success('Pro выдан')
      invalidate()
    },
    onError: () => toast.error('Не удалось выдать Pro'),
  })

  const revokeMutation = useMutation({
    mutationFn: (userId: string) => adminService.revokePro(userId),
    onSuccess: () => {
      toast.success('Pro отозван')
      invalidate()
    },
    onError: () => toast.error('Не удалось отозвать Pro'),
  })

  const adminMutation = useMutation({
    mutationFn: ({ userId, isAdmin }: { userId: string; isAdmin: boolean }) =>
      adminService.setAdmin(userId, isAdmin),
    onSuccess: () => {
      toast.success('Права администратора обновлены')
      invalidate()
    },
    onError: () => toast.error('Не удалось обновить права'),
  })

  const onGrant = (userId: string) => {
    const input = prompt('На сколько дней выдать Pro?', '30')
    if (!input) return
    const days = parseInt(input, 10)
    if (!Number.isFinite(days) || days <= 0) {
      toast.error('Введите положительное число дней')
      return
    }
    grantMutation.mutate({ userId, days })
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-900">Пользователи</h1>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Поиск по email или имени"
            className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
        </div>
        <select
          value={tier}
          onChange={(e) => setTier(e.target.value as 'all' | 'free' | 'pro')}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          <option value="all">Все тарифы</option>
          <option value="free">Free</option>
          <option value="pro">Pro</option>
        </select>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500">
            <tr>
              <th className="text-left px-4 py-3 font-medium">Пользователь</th>
              <th className="text-left px-4 py-3 font-medium">Тариф</th>
              <th className="text-left px-4 py-3 font-medium">Pro до</th>
              <th className="text-left px-4 py-3 font-medium">Документов</th>
              <th className="text-left px-4 py-3 font-medium">Создан</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={6} className="text-center py-8 text-gray-400">
                  <Loader2 className="w-5 h-5 animate-spin inline" />
                </td>
              </tr>
            )}
            {!isLoading && users && users.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-8 text-gray-400">Ничего не найдено</td>
              </tr>
            )}
            {users?.map((u) => (
              <tr key={u.id} className="border-t border-gray-100">
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900 flex items-center gap-2">
                    {u.full_name || '—'}
                    {u.is_admin && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[10px] font-medium">
                        <Shield className="w-3 h-3" /> admin
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-gray-500">{u.email || '(без email)'}</div>
                </td>
                <td className="px-4 py-3">
                  {u.subscription_tier === 'pro' ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 text-xs font-medium">
                      <Crown className="w-3 h-3" /> Pro
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs">Free</span>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-700">{formatDate(u.pro_expires_at)}</td>
                <td className="px-4 py-3 text-gray-700">{u.documents_count}</td>
                <td className="px-4 py-3 text-gray-500">{formatDate(u.created_at)}</td>
                <td className="px-4 py-3 text-right">
                  <div className="inline-flex items-center gap-2">
                    <button
                      onClick={() => onGrant(u.id)}
                      title="Выдать Pro"
                      className="p-1.5 rounded hover:bg-emerald-50 text-emerald-600"
                    >
                      <Crown className="w-4 h-4" />
                    </button>
                    {u.subscription_tier === 'pro' && (
                      <button
                        onClick={() => {
                          if (confirm('Отозвать Pro у пользователя?')) revokeMutation.mutate(u.id)
                        }}
                        title="Отозвать Pro"
                        className="p-1.5 rounded hover:bg-red-50 text-red-600"
                      >
                        <MinusCircle className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => adminMutation.mutate({ userId: u.id, isAdmin: !u.is_admin })}
                      title={u.is_admin ? 'Снять права админа' : 'Сделать админом'}
                      className="p-1.5 rounded hover:bg-blue-50 text-blue-600"
                    >
                      {u.is_admin ? <ShieldOff className="w-4 h-4" /> : <Shield className="w-4 h-4" />}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
