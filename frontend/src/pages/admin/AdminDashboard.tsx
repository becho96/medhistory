import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Users, Crown, Ticket, Activity } from 'lucide-react'
import { adminService } from '../../services/admin'

export default function AdminDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: adminService.getStats,
  })

  const cards = [
    { label: 'Всего пользователей', value: data?.total_users, icon: Users, color: 'text-gray-700' },
    { label: 'Активных Pro', value: data?.pro_users, icon: Crown, color: 'text-amber-600' },
    { label: 'Активных промокодов', value: data?.active_promocodes, icon: Ticket, color: 'text-emerald-600' },
    { label: 'Активаций за месяц', value: data?.activations_this_month, icon: Activity, color: 'text-blue-600' },
  ]

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-900">Администрирование</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c) => (
          <div key={c.label} className="rounded-2xl border border-gray-200 bg-white p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">{c.label}</span>
              <c.icon className={`w-5 h-5 ${c.color}`} />
            </div>
            <div className="text-2xl font-semibold text-gray-900">
              {isLoading ? '…' : c.value ?? 0}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link
          to="/admin/promocodes"
          className="rounded-2xl border border-gray-200 bg-white p-5 hover:border-emerald-300 transition-colors"
        >
          <div className="flex items-center gap-3 mb-2">
            <Ticket className="w-5 h-5 text-emerald-600" />
            <div className="font-semibold text-gray-900">Промокоды</div>
          </div>
          <div className="text-sm text-gray-500">Создание, деактивация и удаление промокодов</div>
        </Link>
        <Link
          to="/admin/users"
          className="rounded-2xl border border-gray-200 bg-white p-5 hover:border-emerald-300 transition-colors"
        >
          <div className="flex items-center gap-3 mb-2">
            <Users className="w-5 h-5 text-gray-700" />
            <div className="font-semibold text-gray-900">Пользователи</div>
          </div>
          <div className="text-sm text-gray-500">Поиск, ручной апгрейд до Pro, права администратора</div>
        </Link>
      </div>
    </div>
  )
}
