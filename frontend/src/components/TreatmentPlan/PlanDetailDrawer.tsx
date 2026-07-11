import { useMemo } from 'react'
import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { X, FileText, ArrowUpRight } from 'lucide-react'
import type { PlanNode, PlanEdge } from '../../services/plans'
import { KIND_META, STATUS_META } from './planLayout'

const fmt = (v?: string | null) => (v ? format(parseISO(v), 'd MMMM yyyy', { locale: ru }) : '')

interface PlanDetailDrawerProps {
  node: PlanNode | null
  nodes: PlanNode[]
  edges: PlanEdge[]
  onClose: () => void
  onSelect: (node: PlanNode) => void
  onOpenDocument?: (documentId: string) => void
}

function RelRow({ node, onClick }: { node: PlanNode; onClick: () => void }) {
  const s = STATUS_META[node.status]
  const Icon = (KIND_META[node.kind] ?? KIND_META.other).Icon
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center gap-2.5 rounded-lg border border-gray-100 bg-white px-3 py-2 text-left transition hover:border-emerald-200"
    >
      <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md text-white ${s.icon}`}>
        <Icon className="h-3 w-3" />
      </span>
      <span className="flex-1 truncate text-[13px] text-gray-800">{node.title}</span>
      <span className={`shrink-0 rounded-full border px-2 py-[1px] text-[10.5px] font-semibold ${s.badge}`}>
        {s.label}
      </span>
    </button>
  )
}

export default function PlanDetailDrawer({
  node, nodes, edges, onClose, onSelect, onOpenDocument,
}: PlanDetailDrawerProps) {
  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes])

  const { parents, children } = useMemo(() => {
    if (!node) return { parents: [] as PlanNode[], children: [] as PlanNode[] }
    const p: PlanNode[] = []
    const c: PlanNode[] = []
    edges.forEach((e) => {
      if (e.target === node.id) { const s = byId.get(e.source); if (s) p.push(s) }
      if (e.source === node.id) { const t = byId.get(e.target); if (t) c.push(t) }
    })
    return { parents: p, children: c }
  }, [node, edges, byId])

  if (!node) return null
  const s = STATUS_META[node.status]
  const Icon = (KIND_META[node.kind] ?? KIND_META.other).Icon
  const isDone = node.status === 'done'

  return (
    <>
      <div className="fixed inset-0 z-40 bg-gray-900/40" onClick={onClose} />
      <aside className="fixed right-0 top-0 z-50 flex h-full w-[min(430px,92vw)] flex-col border-l border-gray-100 bg-white shadow-xl">
        <div className="flex items-start gap-3 border-b border-gray-100 p-5">
          <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-white ${s.icon}`}>
            <Icon className="h-4 w-4" />
          </span>
          <div className="min-w-0 flex-1">
            <h3 className="text-[16px] font-semibold leading-tight text-gray-900">{node.title}</h3>
            <p className="mt-0.5 text-[12.5px] text-gray-500">
              {(KIND_META[node.kind] ?? KIND_META.other).label}
              {(node.date || node.due_date) && ' · ' + fmt(node.date || node.due_date)}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-lg bg-gray-50 p-1.5 text-gray-400 hover:text-gray-700"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto p-5">
          <div>
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-400">Состояние</p>
            <span className={`inline-flex rounded-full border px-3 py-1 text-[12px] font-semibold ${s.badge}`}>
              {s.label}
            </span>
          </div>

          {isDone ? (
            <div>
              <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-400">Документ в медкарте</p>
              <div className="rounded-xl border border-gray-100 bg-gray-50/70 p-3.5">
                <div className="flex items-center gap-2 text-[13.5px] font-semibold text-gray-800">
                  <FileText className="h-4 w-4 text-gray-400" />
                  {node.document_type || 'Документ'}
                </div>
                <p className="mt-1 text-[12px] text-gray-500">
                  {[fmt(node.date), node.doctor, node.facility].filter(Boolean).join(' · ')}
                </p>
                {node.summary && <p className="mt-2 text-[12.5px] leading-relaxed text-gray-600">{node.summary}</p>}
                {node.document_id && onOpenDocument && (
                  <button
                    type="button"
                    onClick={() => onOpenDocument(node.document_id!)}
                    className="mt-3 inline-flex items-center gap-1 text-[12.5px] font-medium text-emerald-600 hover:text-emerald-700"
                  >
                    Открыть документ
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div>
              <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-400">Ожидается документ</p>
              <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50/70 p-3.5">
                <div className="flex items-center gap-2 text-[13.5px] font-semibold text-gray-600">
                  <FileText className="h-4 w-4 text-gray-400" />
                  {node.document_type || 'Назначение'}
                </div>
                {node.due_date && (
                  <p className={`mt-1.5 text-[12.5px] font-medium ${node.status === 'overdue' ? 'text-red-600' : 'text-gray-500'}`}>
                    Срок: {fmt(node.due_date)}
                  </p>
                )}
              </div>
            </div>
          )}

          {parents.length > 0 && (
            <div>
              <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-400">Назначено на приёме</p>
              <div className="space-y-1.5">
                {parents.map((p) => <RelRow key={p.id} node={p} onClick={() => onSelect(p)} />)}
              </div>
              {node.merge_count > 1 && (
                <p className="mt-2 text-[11.5px] leading-relaxed text-gray-400">
                  Назначено несколькими специалистами — достаточно выполнить один раз, результат закроет все направления.
                </p>
              )}
            </div>
          )}

          {children.length > 0 && (
            <div>
              <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-400">По результату назначено</p>
              <div className="space-y-1.5">
                {children.map((c) => <RelRow key={c.id} node={c} onClick={() => onSelect(c)} />)}
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  )
}
