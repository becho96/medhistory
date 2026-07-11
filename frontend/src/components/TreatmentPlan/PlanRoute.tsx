import { useMemo } from 'react'
import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { Check, GitMerge } from 'lucide-react'
import type { PlanNode } from '../../services/plans'
import { KIND_META, STATUS_META } from './planLayout'

const fmt = (v?: string | null) => (v ? format(parseISO(v), 'd MMMM', { locale: ru }) : '')

interface PlanRouteProps {
  nodes: PlanNode[]
  onSelect: (node: PlanNode) => void
}

interface Group {
  title: string
  hint: string
  match: (n: PlanNode) => boolean
  highlight?: boolean
}

const GROUPS: Group[] = [
  { title: 'Сейчас важно', hint: 'Просроченные шаги — стоит запланировать', match: (n) => n.status === 'overdue', highlight: true },
  { title: 'Дальше по плану', hint: 'Назначено, но ещё не выполнено', match: (n) => n.status === 'planned' },
  { title: 'Уже сделано', hint: 'Документы в медкарте', match: (n) => n.status === 'done' },
]

function StepCard({ node, onSelect, highlight }: { node: PlanNode; onSelect: (n: PlanNode) => void; highlight?: boolean }) {
  const s = STATUS_META[node.status]
  const meta = KIND_META[node.kind] ?? KIND_META.other
  const Icon = meta.Icon
  const isDone = node.status === 'done'
  return (
    <button
      type="button"
      onClick={() => onSelect(node)}
      className={`flex w-full items-center gap-3 rounded-xl border p-3.5 text-left transition hover:border-emerald-200 ${s.card} ${highlight ? 'ring-2 ring-red-100' : ''}`}
    >
      <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white ${s.icon}`}>
        {isDone ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[14.5px] font-semibold text-gray-900">{node.title}</p>
        <p className="mt-0.5 text-[12.5px] text-gray-500">
          {isDone
            ? [fmt(node.date), node.doctor].filter(Boolean).join(' · ')
            : node.due_date
              ? `Срок: ${fmt(node.due_date)}`
              : meta.label}
        </p>
      </div>
      {node.merge_count > 1 && (
        <span className="flex shrink-0 items-center gap-1 rounded-full bg-teal-50 px-2 py-1 text-[11px] font-semibold text-teal-700">
          <GitMerge className="h-3 w-3" />
          Нужен нескольким врачам
        </span>
      )}
    </button>
  )
}

export default function PlanRoute({ nodes, onSelect }: PlanRouteProps) {
  const groups = useMemo(
    () => GROUPS.map((g) => ({ ...g, items: nodes.filter(g.match) })).filter((g) => g.items.length > 0),
    [nodes],
  )
  const done = nodes.filter((n) => n.status === 'done').length
  const pct = nodes.length ? Math.round((done / nodes.length) * 100) : 0

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-4 rounded-2xl border border-gray-100 bg-white p-5">
        <span className="text-[22px] font-semibold tabular-nums text-gray-900">{pct}%</span>
        <div className="h-2.5 min-w-[180px] flex-1 overflow-hidden rounded-full bg-gray-100">
          <div className="h-full rounded-full bg-emerald-500" style={{ width: `${pct}%` }} />
        </div>
        <span className="text-[13px] text-gray-500">{done} из {nodes.length} шагов выполнено</span>
      </div>

      {groups.map((g) => (
        <div key={g.title}>
          <div className="mb-3">
            <h3 className="text-[12px] font-semibold uppercase tracking-wide text-gray-400">{g.title}</h3>
            <p className="text-[12px] text-gray-400">{g.hint}</p>
          </div>
          <div className="space-y-2.5">
            {g.items.map((n) => <StepCard key={n.id} node={n} onSelect={onSelect} highlight={g.highlight} />)}
          </div>
        </div>
      ))}
    </div>
  )
}
