import { useState, type ReactNode } from 'react'
import { Check } from 'lucide-react'

export type MissingFieldKey = 'document_date' | 'patient_name' | 'doctor_name'

export interface MissingFieldDef {
  key: MissingFieldKey
  icon: ReactNode
  label: string
  type: 'date' | 'text'
  placeholder?: string
  hint?: string
}

interface MissingFieldsPanelProps {
  fields: MissingFieldDef[]
  isSaving: boolean
  onSave: (key: MissingFieldKey, value: string) => void
}

// Одна строка редактора конкретного поля. Держит собственный ввод, чтобы
// поля не мешали друг другу.
function MissingFieldRow({
  field,
  isSaving,
  onSave,
}: {
  field: MissingFieldDef
  isSaving: boolean
  onSave: (key: MissingFieldKey, value: string) => void
}) {
  const [value, setValue] = useState('')
  const today = new Date().toISOString().slice(0, 10)
  const trimmed = value.trim()

  const handleSave = () => {
    if (!trimmed || isSaving) return
    onSave(field.key, trimmed)
  }

  return (
    <div className="flex flex-col gap-2 px-3 py-2.5">
      <div className="flex items-center gap-2">
        <span className="text-amber-600 shrink-0">{field.icon}</span>
        <span className="text-xs font-medium text-amber-800">{field.label}</span>
      </div>
      <div className="flex items-center gap-2">
        <input
          type={field.type}
          value={value}
          max={field.type === 'date' ? today : undefined}
          placeholder={field.placeholder}
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
      {field.hint && <p className="text-[11px] leading-4 text-amber-700">{field.hint}</p>}
    </div>
  )
}

// Единый блок для заполнения любых обязательных полей, которые не удалось
// распознать автоматически. Показывается ситуативно — только когда список
// недостающих полей не пуст.
export default function MissingFieldsPanel({ fields, isSaving, onSave }: MissingFieldsPanelProps) {
  if (!fields.length) return null

  return (
    <div className="overflow-hidden rounded-xl border border-amber-200 bg-amber-50">
      <div className="border-b border-amber-200/70 px-3 py-2">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-amber-800">
          Заполните недостающие данные
        </h4>
        <p className="mt-0.5 text-[11px] leading-4 text-amber-700">
          Эти поля не удалось распознать автоматически — добавьте их вручную.
        </p>
      </div>
      <div className="divide-y divide-amber-200/60">
        {fields.map((field) => (
          <MissingFieldRow key={field.key} field={field} isSaving={isSaving} onSave={onSave} />
        ))}
      </div>
    </div>
  )
}
