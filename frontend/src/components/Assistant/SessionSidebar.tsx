import { Plus, Trash2, MessageSquare } from 'lucide-react'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'
import type { AssistantSession } from '../../services/assistant'

// date-fns/locale/ru may not be available — safe fallback
const formatDate = (iso: string) => {
  try {
    return format(new Date(iso), 'd MMM', { locale: ru })
  } catch {
    return new Date(iso).toLocaleDateString()
  }
}

interface Props {
  sessions: AssistantSession[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
  loading?: boolean
}

export default function SessionSidebar({
  sessions, activeId, onSelect, onNew, onDelete, loading,
}: Props) {
  return (
    <div className="flex flex-col h-full bg-white/60 backdrop-blur-sm border-r border-gray-100">
      <div className="p-4 border-b border-gray-100">
        <button
          onClick={onNew}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
            bg-gradient-to-br from-[#4A90E2] to-[#3A7BC8] text-white text-sm font-medium
            shadow-md hover:shadow-lg transition-all active:scale-95"
        >
          <Plus className="w-4 h-4" />
          Новый чат
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {loading ? (
          <div className="space-y-2 p-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 bg-gray-100 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-center px-4">
            <MessageSquare className="w-8 h-8 text-gray-300 mb-2" />
            <p className="text-sm text-gray-400">Нет диалогов</p>
            <p className="text-xs text-gray-300 mt-1">Начните новый чат</p>
          </div>
        ) : (
          sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => onSelect(s.id)}
              className={`group flex items-start gap-3 p-3 rounded-xl cursor-pointer transition-all mb-1
                ${activeId === s.id
                  ? 'bg-gradient-to-br from-[#4A90E2]/10 to-[#3A7BC8]/10 border border-[#4A90E2]/20'
                  : 'hover:bg-gray-50'
                }`}
            >
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5
                ${activeId === s.id ? 'bg-[#4A90E2]/20' : 'bg-gray-100'}`}>
                <MessageSquare className={`w-4 h-4 ${activeId === s.id ? 'text-[#4A90E2]' : 'text-gray-400'}`} />
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium truncate
                  ${activeId === s.id ? 'text-[#4A90E2]' : 'text-gray-800'}`}>
                  {s.title}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">{formatDate(s.updated_at)}</p>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); onDelete(s.id) }}
                className="opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-red-50
                  hover:text-red-500 text-gray-400 transition-all flex-shrink-0"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
