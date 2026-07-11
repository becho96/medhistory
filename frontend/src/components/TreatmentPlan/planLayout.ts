import { Stethoscope, FlaskConical, ScanLine, Activity, FileText } from 'lucide-react'
import type { PlanNode, PlanEdge, PlanKind, PlanStatus } from '../../services/plans'

// ---- Визуальная мета узлов ----
export const KIND_META: Record<PlanKind, { label: string; Icon: typeof Stethoscope }> = {
  consultation: { label: 'Приём', Icon: Stethoscope },
  lab: { label: 'Анализ', Icon: FlaskConical },
  instrumental: { label: 'Исследование', Icon: ScanLine },
  functional: { label: 'Функц. диагностика', Icon: Activity },
  other: { label: 'Документ', Icon: FileText },
}

export const STATUS_META: Record<PlanStatus, {
  label: string; card: string; icon: string; badge: string; dot: string
}> = {
  done: {
    label: 'Выполнено',
    card: 'border-emerald-200 bg-white',
    icon: 'bg-emerald-500',
    badge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    dot: 'bg-emerald-500',
  },
  planned: {
    label: 'Планируется',
    card: 'border-dashed border-gray-300 bg-gray-50/70',
    icon: 'bg-gray-400',
    badge: 'bg-white text-gray-500 border-gray-300 border-dashed',
    dot: 'bg-gray-300',
  },
  overdue: {
    label: 'Просрочено',
    card: 'border-red-200 bg-red-50',
    icon: 'bg-red-500',
    badge: 'bg-white text-red-600 border-red-200',
    dot: 'bg-red-500',
  },
}

// ---- Раскладка эпизода: слои по глубине × дорожки по специальностям ----
export interface LaidOutNode extends PlanNode {
  x: number
  y: number
  laneKey: string
}
export interface LaidOutLane {
  key: string
  label: string
  top: number
  height: number
  color: string
}
export interface PlanLayout {
  nodes: LaidOutNode[]
  lanes: LaidOutLane[]
  width: number
  height: number
  nodeW: number
  nodeH: number
}

const NODE_W = 194
const NODE_H = 62
const COL_W = 228
const ROW_H = 88
const GUTTER = 150
const PAD_TOP = 40
const PAD_BOT = 24

const LANE_COLORS = ['#0d9488', '#7c5cc4', '#3a76c9', '#c25b7e', '#4d9e6a', '#b06a2a']
const DIAG_COLOR = '#b0812f'

export function layoutEpisode(nodes: PlanNode[], edges: PlanEdge[]): PlanLayout {
  const ids = new Set(nodes.map((n) => n.id))
  const indegInit = new Map<string, number>()
  const outgoing = new Map<string, string[]>()
  nodes.forEach((n) => {
    indegInit.set(n.id, 0)
    outgoing.set(n.id, [])
  })
  edges.forEach((e) => {
    if (!ids.has(e.source) || !ids.has(e.target)) return
    outgoing.get(e.source)!.push(e.target)
    indegInit.set(e.target, (indegInit.get(e.target) || 0) + 1)
  })

  // Глубина = длиннейший путь от корня (топологически, Кан).
  const depth = new Map<string, number>()
  const indeg = new Map(indegInit)
  const queue: string[] = []
  nodes.forEach((n) => {
    if ((indeg.get(n.id) || 0) === 0) {
      depth.set(n.id, 0)
      queue.push(n.id)
    }
  })
  while (queue.length) {
    const u = queue.shift()!
    const du = depth.get(u) || 0
    for (const v of outgoing.get(u) || []) {
      depth.set(v, Math.max(depth.get(v) ?? 0, du + 1))
      indeg.set(v, (indeg.get(v) || 0) - 1)
      if ((indeg.get(v) || 0) === 0) queue.push(v)
    }
  }
  nodes.forEach((n) => {
    if (!depth.has(n.id)) depth.set(n.id, 0) // защита от циклов
  })

  const laneKeyOf = (n: PlanNode) =>
    n.kind === 'consultation' ? 'sp:' + (n.specialty || n.title) : 'diag'
  const laneLabelOf = (n: PlanNode) =>
    n.kind === 'consultation' ? n.specialty || 'Приём' : 'Диагностика'

  const byLane = new Map<string, PlanNode[]>()
  nodes.forEach((n) => {
    const k = laneKeyOf(n)
    if (!byLane.has(k)) byLane.set(k, [])
    byLane.get(k)!.push(n)
  })

  // Дорожки-специальности по минимальной глубине участников; «Диагностика» — вниз.
  const minDepth = (k: string) => Math.min(...byLane.get(k)!.map((n) => depth.get(n.id) || 0))
  const laneKeys = [...byLane.keys()].sort((a, b) => {
    if (a === 'diag') return 1
    if (b === 'diag') return -1
    return minDepth(a) - minDepth(b)
  })

  const laidNodes: LaidOutNode[] = []
  const lanes: LaidOutLane[] = []
  let row = 0
  let colorIdx = 0
  laneKeys.forEach((k) => {
    const members = byLane.get(k)!.slice().sort((a, b) => {
      const da = depth.get(a.id) || 0
      const db = depth.get(b.id) || 0
      if (da !== db) return da - db
      return (a.date || a.due_date || '').localeCompare(b.date || b.due_date || '')
    })
    const laneTop = PAD_TOP + row * ROW_H
    members.forEach((n) => {
      laidNodes.push({
        ...n,
        laneKey: k,
        x: GUTTER + (depth.get(n.id) || 0) * COL_W,
        y: PAD_TOP + row * ROW_H + (ROW_H - NODE_H) / 2,
      })
      row++
    })
    lanes.push({
      key: k,
      label: laneLabelOf(members[0]),
      top: laneTop,
      height: members.length * ROW_H,
      color: k === 'diag' ? DIAG_COLOR : LANE_COLORS[colorIdx++ % LANE_COLORS.length],
    })
  })

  const maxDepth = Math.max(0, ...nodes.map((n) => depth.get(n.id) || 0))
  const width = GUTTER + maxDepth * COL_W + NODE_W + 40
  const height = PAD_TOP + row * ROW_H + PAD_BOT

  return { nodes: laidNodes, lanes, width, height, nodeW: NODE_W, nodeH: NODE_H }
}
