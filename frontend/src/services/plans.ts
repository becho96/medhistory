import { api } from '../lib/api'

export type PlanKind = 'consultation' | 'lab' | 'instrumental' | 'functional' | 'other'
export type PlanStatus = 'done' | 'planned' | 'overdue'

export interface PlanNode {
  id: string
  kind: PlanKind
  status: PlanStatus
  title: string
  subtitle?: string | null
  date?: string | null
  due_date?: string | null
  doctor?: string | null
  facility?: string | null
  specialty?: string | null
  summary?: string | null
  document_type?: string | null
  document_id?: string | null
  merge_count: number
}

export interface PlanEdge {
  source: string
  target: string
  kind: string
}

export interface PlanEpisode {
  id: string
  title: string
  root_id: string
  custom_name: boolean
  node_ids: string[]
  done: number
  total: number
  start_date?: string | null
  end_date?: string | null
}

export interface PlanOverride {
  id: string
  kind: string
  anchor_key: string
  other_key?: string | null
  title?: string | null
}

export interface PlanGraph {
  episodes: PlanEpisode[]
  nodes: PlanNode[]
  edges: PlanEdge[]
  overrides: PlanOverride[]
  generated_at: string
}

export interface PlanOverrideCreate {
  kind: 'rename' | 'merge'
  anchor_key: string
  other_key?: string | null
  title?: string | null
}

export const plansService = {
  getGraph: async (): Promise<PlanGraph> => (await api.get('/plans/graph')).data,

  createOverride: async (input: PlanOverrideCreate): Promise<PlanOverride> =>
    (await api.post('/plans/overrides', input)).data,

  deleteOverride: async (id: string): Promise<void> => {
    await api.delete(`/plans/overrides/${id}`)
  },
}
