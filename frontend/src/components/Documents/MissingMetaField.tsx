import { useState, type ReactNode } from 'react'
import { Check } from 'lucide-react'

interface MissingMetaFieldProps {
  icon: ReactNode
  label: string
  type: 'date' | 'text'
  placeholder?: string
  hint?: string
  isSaving: boolean
  onSave: (value: string) => void
}

// Ситуативный редактор обязательного поля, которого нет у документа.
// Показывается только когда значение отсутствует; после сохранения строка
// заменяется обычным отображением значения (родитель перестаёт её рендерить).
export default function MissingMetaField({
  icon,
  label,
  type,
  placeholder,
  hint,
  isSaving,
  onSave,
}: MissingMetaFieldProps) {
  const [value, setValue] = useState('')
  const today = new Date().toISOString().slice(0, 10)
  const trimmed = value.trim()

  const handleSave = () => {
    if (!trimmed || isSaving) return
    onSave(trimmed)
  }

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5">
      <div className="flex items-center gap-2">
        <span className="text-amber-600 shrink-0">{icon}</span>
        <span className="text-xs font-medium text-amber-800">{label} не указана — добавьте вручную</span>
      </div>
      <div className="flex items-center gap-2">
        <input
          type={type}
          value={value}
          max={type === 'date' ? today : undefined}
          placeholder={placeholder}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSave() }}
          className="h-9 min-w-0 flex-1 rounded-lg border border-amber-200 bg-white px-2.5 text-sm text-gray-900 outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
        />
        <button
          type="button"
          onClick={handleSave}
          disabled={!trimmed || isSaving}
          className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-amber-500 px-3 text-sm font-medium text-white disabled:opacity-50"
        >
          <Check className="h-4 w-4" />
          Сохранить
        </button>
      </div>
      {hint && <p className="text-[11px] leading-4 text-amber-700">{hint}</p>}
    </div>
  )
}
