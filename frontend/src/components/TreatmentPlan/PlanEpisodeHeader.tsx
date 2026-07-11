import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Pencil, Check, X, GitMerge, RotateCcw, ChevronDown } from 'lucide-react'
import { plansService, type PlanEpisode, type PlanOverride } from '../../services/plans'

interface PlanEpisodeHeaderProps {
  episode: PlanEpisode
  episodes: PlanEpisode[]
  overrides: PlanOverride[]
  onAfterMerge: (rootId: string) => void
}

export default function PlanEpisodeHeader({ episode, episodes, overrides, onAfterMerge }: PlanEpisodeHeaderProps) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(episode.title)
  const [mergeOpen, setMergeOpen] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setEditing(false)
    setName(episode.title)
  }, [episode.id, episode.title])

  useEffect(() => {
    if (editing) inputRef.current?.focus()
  }, [editing])

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['plan', 'graph'] })

  const renameMutation = useMutation({
    mutationFn: (title: string) =>
      plansService.createOverride({ kind: 'rename', anchor_key: episode.root_id, title }),
    onSuccess: () => { invalidate(); setEditing(false); toast.success('Эпизод переименован') },
    onError: () => toast.error('Не удалось переименовать'),
  })

  const renameOverride = overrides.find((o) => o.kind === 'rename' && o.anchor_key === episode.root_id)
  const resetMutation = useMutation({
    mutationFn: (id: string) => plansService.deleteOverride(id),
    onSuccess: () => { invalidate(); toast.success('Имя сброшено') },
    onError: () => toast.error('Не удалось сбросить'),
  })

  const mergeMutation = useMutation({
    mutationFn: (otherRootId: string) =>
      plansService.createOverride({ kind: 'merge', anchor_key: episode.root_id, other_key: otherRootId }),
    onSuccess: () => { invalidate(); setMergeOpen(false); onAfterMerge(episode.root_id); toast.success('Эпизоды объединены') },
    onError: () => toast.error('Не удалось объединить'),
  })

  const submitRename = () => {
    const trimmed = name.trim()
    if (!trimmed || trimmed === episode.title) { setEditing(false); return }
    renameMutation.mutate(trimmed)
  }

  const others = episodes.filter((e) => e.id !== episode.id)

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-gray-100 bg-white px-5 py-3.5">
      <div className="flex min-w-0 items-center gap-2">
        {editing ? (
          <div className="flex items-center gap-1.5">
            <input
              ref={inputRef}
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') submitRename(); if (e.key === 'Escape') setEditing(false) }}
              maxLength={200}
              className="w-64 max-w-full rounded-lg border border-gray-200 px-2.5 py-1.5 text-[15px] font-semibold text-gray-900 outline-none focus:border-emerald-400"
            />
            <button type="button" onClick={submitRename} className="rounded-lg p-1.5 text-emerald-600 hover:bg-emerald-50" title="Сохранить">
              <Check className="h-4 w-4" />
            </button>
            <button type="button" onClick={() => setEditing(false)} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100" title="Отмена">
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <>
            <h2 className="truncate text-[16px] font-semibold text-gray-900">{episode.title}</h2>
            <button
              type="button"
              onClick={() => { setName(episode.title); setEditing(true) }}
              className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
              title="Переименовать эпизод"
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>
            {episode.custom_name && renameOverride && (
              <button
                type="button"
                onClick={() => resetMutation.mutate(renameOverride.id)}
                className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[12px] text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                title="Вернуть авто-название"
              >
                <RotateCcw className="h-3 w-3" />
                сбросить
              </button>
            )}
          </>
        )}
      </div>

      {others.length > 0 && (
        <div className="relative">
          <button
            type="button"
            onClick={() => setMergeOpen((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-[13px] font-medium text-gray-600 hover:border-gray-300"
          >
            <GitMerge className="h-3.5 w-3.5" />
            Объединить с…
            <ChevronDown className="h-3.5 w-3.5" />
          </button>
          {mergeOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMergeOpen(false)} />
              <div className="absolute right-0 z-20 mt-1.5 w-64 rounded-xl border border-gray-100 bg-white p-1.5 shadow-lg">
                {others.map((e) => (
                  <button
                    key={e.id}
                    type="button"
                    onClick={() => mergeMutation.mutate(e.root_id)}
                    className="block w-full truncate rounded-lg px-3 py-2 text-left text-[13px] text-gray-700 hover:bg-emerald-50"
                  >
                    {e.title}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
