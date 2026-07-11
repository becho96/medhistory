import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Network, ArrowRight, GitMerge } from 'lucide-react'
import { plansService, type PlanEpisode } from '../../services/plans'

// Ближайший значимый шаг эпизода: сперва просроченное, затем планируемое.
function nextStepLabel(episode: PlanEpisode, nodeStatus: Map<string, string>, nodeTitle: Map<string, string>): string | null {
  const overdue = episode.node_ids.find((id) => nodeStatus.get(id) === 'overdue')
  if (overdue) return nodeTitle.get(overdue) ?? null
  const planned = episode.node_ids.find((id) => nodeStatus.get(id) === 'planned')
  if (planned) return nodeTitle.get(planned) ?? null
  return null
}

export default function TreatmentPlanCard() {
  const { data } = useQuery({
    queryKey: ['plan', 'graph'],
    queryFn: () => plansService.getGraph(),
  })

  const { statusById, titleById } = useMemo(() => {
    const statusById = new Map<string, string>()
    const titleById = new Map<string, string>()
    data?.nodes.forEach((n) => {
      statusById.set(n.id, n.status)
      titleById.set(n.id, n.title)
    })
    return { statusById, titleById }
  }, [data])

  const episodes = data?.episodes ?? []
  if (episodes.length === 0) return null

  // Ведущий эпизод — с наибольшим числом незакрытых шагов.
  const primary = [...episodes].sort((a, b) => (b.total - b.done) - (a.total - a.done))[0]
  const pct = primary.total ? Math.round((primary.done / primary.total) * 100) : 0
  const hasMerge = data?.nodes.some((n) => primary.node_ids.includes(n.id) && n.merge_count > 1)
  const next = nextStepLabel(primary, statusById, titleById)
  const overdueCount = primary.node_ids.filter((id) => statusById.get(id) === 'overdue').length

  return (
    <Link
      to="/plan"
      className="group block rounded-2xl border border-gray-100 bg-white p-6 transition-colors hover:border-emerald-200"
    >
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="flex items-center gap-2 text-[15px] font-semibold text-gray-900">
            <Network className="h-4 w-4 text-emerald-500" />
            План лечения
          </h3>
          <p className="mt-0.5 text-[12px] text-gray-400">Как связаны приёмы, направления и результаты</p>
        </div>
        <span className="flex items-center gap-1 text-[13px] font-medium text-emerald-600 transition-colors group-hover:text-emerald-700">
          Открыть
          <ArrowRight className="h-3.5 w-3.5" />
        </span>
      </div>

      <div className="rounded-xl border border-gray-100 bg-gray-50/60 p-4">
        <div className="mb-2.5 flex items-center justify-between gap-3">
          <p className="truncate text-[14px] font-medium text-gray-900">{primary.title}</p>
          <span className="shrink-0 text-[12.5px] tabular-nums text-gray-400">{primary.done}/{primary.total}</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-gray-200">
          <div className="h-full rounded-full bg-emerald-500" style={{ width: `${pct}%` }} />
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          {next && (
            <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] font-medium ${overdueCount > 0 ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-700'}`}>
              {overdueCount > 0 ? 'Просрочено' : 'Дальше'}: {next}
            </span>
          )}
          {hasMerge && (
            <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2.5 py-1 text-[12px] font-medium text-teal-700">
              <GitMerge className="h-3 w-3" />
              Общее исследование
            </span>
          )}
          {episodes.length > 1 && (
            <span className="text-[12px] text-gray-400">ещё {episodes.length - 1} план(а)</span>
          )}
        </div>
      </div>
    </Link>
  )
}
