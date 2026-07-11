import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Network, LayoutGrid, ListChecks, ArrowLeft, GitMerge } from 'lucide-react'
import { plansService, type PlanNode } from '../services/plans'
import PlanGraph from '../components/TreatmentPlan/PlanGraph'
import PlanRoute from '../components/TreatmentPlan/PlanRoute'
import PlanDetailDrawer from '../components/TreatmentPlan/PlanDetailDrawer'
import PlanEpisodeHeader from '../components/TreatmentPlan/PlanEpisodeHeader'
import DocumentModal from '../components/Documents/DocumentModal'

type ViewMode = 'doctor' | 'patient'

export default function TreatmentPlan() {
  const { data, isLoading } = useQuery({
    queryKey: ['plan', 'graph'],
    queryFn: () => plansService.getGraph(),
  })

  const [episodeId, setEpisodeId] = useState<string | null>(null)
  const [view, setView] = useState<ViewMode>('doctor')
  const [selected, setSelected] = useState<PlanNode | null>(null)
  const [docModalId, setDocModalId] = useState<string | null>(null)

  const episodes = useMemo(() => data?.episodes ?? [], [data])
  const activeEpisode = useMemo(
    () => episodes.find((e) => e.id === episodeId) ?? episodes[0] ?? null,
    [episodes, episodeId],
  )

  const { nodes, edges } = useMemo(() => {
    if (!data || !activeEpisode) return { nodes: [] as PlanNode[], edges: [] }
    const idSet = new Set(activeEpisode.node_ids)
    return {
      nodes: data.nodes.filter((n) => idSet.has(n.id)),
      edges: data.edges.filter((e) => idSet.has(e.source) && idSet.has(e.target)),
    }
  }, [data, activeEpisode])

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to="/" className="mb-2 inline-flex items-center gap-1 text-[13px] text-gray-400 hover:text-gray-600">
            <ArrowLeft className="h-3.5 w-3.5" />
            На главную
          </Link>
          <h1 className="flex items-center gap-2 text-[26px] font-semibold tracking-tight text-gray-900">
            <Network className="h-6 w-6 text-emerald-500" />
            План лечения
          </h1>
          <p className="mt-0.5 text-[13.5px] text-gray-500">
            Как связаны приёмы, направления и результаты в вашей истории болезни
          </p>
        </div>

        <div className="inline-flex rounded-xl border border-gray-200 bg-gray-50 p-1">
          <button
            type="button"
            onClick={() => setView('doctor')}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-[13px] font-medium transition ${view === 'doctor' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}
          >
            <LayoutGrid className="h-4 w-4" />
            Граф
          </button>
          <button
            type="button"
            onClick={() => setView('patient')}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-[13px] font-medium transition ${view === 'patient' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}
          >
            <ListChecks className="h-4 w-4" />
            Маршрут
          </button>
        </div>
      </div>

      {episodes.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {episodes.map((e) => (
            <button
              key={e.id}
              type="button"
              onClick={() => setEpisodeId(e.id)}
              className={`rounded-full border px-3.5 py-1.5 text-[13px] font-medium transition ${activeEpisode?.id === e.id ? 'border-emerald-300 bg-emerald-50 text-emerald-700' : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'}`}
            >
              {e.title}
              <span className="ml-1.5 tabular-nums text-gray-400">{e.done}/{e.total}</span>
            </button>
          ))}
        </div>
      )}

      {isLoading ? (
        <div className="rounded-2xl border border-gray-100 bg-white p-12 text-center text-[14px] text-gray-400">
          Загружаем план лечения…
        </div>
      ) : !activeEpisode ? (
        <div className="rounded-2xl border border-gray-100 bg-white p-12 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-gray-50">
            <Network className="h-6 w-6 text-gray-300" />
          </div>
          <p className="mb-1 text-[15px] font-medium text-gray-900">Пока нет плана лечения</p>
          <p className="text-[13px] text-gray-500">
            План соберётся сам, когда в документах появятся направления от врача
          </p>
        </div>
      ) : (
        <>
          <PlanEpisodeHeader
            episode={activeEpisode}
            episodes={episodes}
            overrides={data?.overrides ?? []}
            onAfterMerge={(rootId) => setEpisodeId(rootId)}
          />
          {view === 'doctor' ? (
            <div className="space-y-3">
              {nodes.some((n) => n.merge_count > 1) && (
            <p className="flex items-center gap-1.5 text-[12.5px] text-gray-500">
              <GitMerge className="h-3.5 w-3.5 text-teal-600" />
              Значок слияния — исследование, назначенное несколькими врачами: достаточно выполнить один раз
            </p>
          )}
              <PlanGraph nodes={nodes} edges={edges} onSelect={setSelected} />
            </div>
          ) : (
            <PlanRoute nodes={nodes} onSelect={setSelected} />
          )}
        </>
      )}

      <PlanDetailDrawer
        node={selected}
        nodes={nodes}
        edges={edges}
        onClose={() => setSelected(null)}
        onSelect={setSelected}
        onOpenDocument={(id) => { setSelected(null); setDocModalId(id) }}
      />

      {docModalId && (
        <DocumentModal documentId={docModalId} onClose={() => setDocModalId(null)} />
      )}
    </div>
  )
}
