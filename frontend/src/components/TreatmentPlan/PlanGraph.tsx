import { useMemo, useState } from 'react'
import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { GitMerge } from 'lucide-react'
import type { PlanNode, PlanEdge } from '../../services/plans'
import { layoutEpisode, KIND_META, STATUS_META, type LaidOutNode } from './planLayout'

const fmt = (v?: string | null) => (v ? format(parseISO(v), 'd MMM', { locale: ru }) : '')

function borderPoint(n: LaidOutNode, w: number, h: number, tx: number, ty: number) {
  const cx = n.x + w / 2
  const cy = n.y + h / 2
  const dx = tx - cx
  const dy = ty - cy
  if (dx === 0 && dy === 0) return { x: cx, y: cy }
  const hw = w / 2 + 2
  const hh = h / 2 + 2
  const t = Math.min(
    dx === 0 ? Infinity : hw / Math.abs(dx),
    dy === 0 ? Infinity : hh / Math.abs(dy),
  )
  return { x: cx + dx * t, y: cy + dy * t }
}

function edgePath(a: LaidOutNode, b: LaidOutNode, w: number, h: number) {
  const ac = { x: a.x + w / 2, y: a.y + h / 2 }
  const bc = { x: b.x + w / 2, y: b.y + h / 2 }
  const p1 = borderPoint(a, w, h, bc.x, bc.y)
  const p2 = borderPoint(b, w, h, ac.x, ac.y)
  const mx = (p1.x + p2.x) / 2
  return `M ${p1.x} ${p1.y} C ${mx} ${p1.y}, ${mx} ${p2.y}, ${p2.x} ${p2.y}`
}

interface PlanGraphProps {
  nodes: PlanNode[]
  edges: PlanEdge[]
  onSelect: (node: PlanNode) => void
}

export default function PlanGraph({ nodes, edges, onSelect }: PlanGraphProps) {
  const layout = useMemo(() => layoutEpisode(nodes, edges), [nodes, edges])
  const [hover, setHover] = useState<string | null>(null)

  const posById = useMemo(
    () => new Map(layout.nodes.map((n) => [n.id, n])),
    [layout.nodes],
  )
  const neighbors = useMemo(() => {
    const map = new Map<string, Set<string>>()
    edges.forEach((e) => {
      if (!map.has(e.source)) map.set(e.source, new Set())
      if (!map.has(e.target)) map.set(e.target, new Set())
      map.get(e.source)!.add(e.target)
      map.get(e.target)!.add(e.source)
    })
    return map
  }, [edges])

  const isActive = (id: string) =>
    !hover || hover === id || neighbors.get(hover)?.has(id)

  return (
    <div className="overflow-x-auto rounded-2xl border border-gray-100 bg-white">
      <div className="relative" style={{ width: layout.width, height: layout.height }}>
        {/* Дорожки */}
        {layout.lanes.map((l) => (
          <div key={l.key} className="absolute left-0 right-0" style={{ top: l.top, height: l.height }}>
            <div className="absolute inset-0" style={{ backgroundColor: l.color + '12' }} />
            <div className="absolute left-3 top-2 flex items-center gap-1.5 text-[12px] font-semibold text-gray-500">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: l.color }} />
              {l.label}
            </div>
          </div>
        ))}

        {/* Рёбра-направления */}
        <svg
          className="absolute inset-0"
          width={layout.width}
          height={layout.height}
          style={{ overflow: 'visible', pointerEvents: 'none' }}
        >
          <defs>
            <marker id="pg-arrow" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0.5 1 L9 5 L0.5 9 z" fill="#94a3b8" />
            </marker>
          </defs>
          {edges.map((e, i) => {
            const a = posById.get(e.source)
            const b = posById.get(e.target)
            if (!a || !b) return null
            const on = hover ? e.source === hover || e.target === hover : false
            return (
              <path
                key={i}
                d={edgePath(a, b, layout.nodeW, layout.nodeH)}
                fill="none"
                stroke={on ? '#475569' : '#cbd5e1'}
                strokeWidth={on ? 2.4 : 1.6}
                markerEnd="url(#pg-arrow)"
                opacity={hover && !on ? 0.12 : 0.9}
              />
            )
          })}
        </svg>

        {/* Узлы */}
        {layout.nodes.map((n) => {
          const s = STATUS_META[n.status]
          const meta = KIND_META[n.kind] ?? KIND_META.other
          const Icon = meta.Icon
          const when = n.date || n.due_date
          return (
            <button
              key={n.id}
              type="button"
              onMouseEnter={() => setHover(n.id)}
              onMouseLeave={() => setHover(null)}
              onClick={() => onSelect(n)}
              className={`absolute flex flex-col gap-1 rounded-xl border p-2.5 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${s.card} ${isActive(n.id) ? '' : 'opacity-30'}`}
              style={{ left: n.x, top: n.y, width: layout.nodeW }}
            >
              <span className={`absolute -top-2 right-2.5 rounded-full border px-2 py-[1px] text-[10.5px] font-semibold ${s.badge}`}>
                {s.label}
              </span>
              {n.merge_count > 1 && (
                <span className="absolute -top-2 left-2.5 flex items-center gap-1 rounded-full bg-teal-600 px-1.5 py-[1px] text-[10px] font-bold text-white">
                  <GitMerge className="h-2.5 w-2.5" />
                  {n.merge_count}
                </span>
              )}
              <div className="flex items-center gap-1.5">
                <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md text-white ${s.icon}`}>
                  <Icon className="h-3 w-3" />
                </span>
                <span className="truncate text-[13px] font-semibold text-gray-900">{n.title}</span>
              </div>
              <div className="flex items-center gap-1.5 text-[11.5px] text-gray-500">
                {when && <span className="tabular-nums">{fmt(when)}</span>}
                {n.doctor && (
                  <>
                    {when && <span className="text-gray-300">·</span>}
                    <span className="truncate text-gray-400">{n.doctor}</span>
                  </>
                )}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
