import { useState } from 'react'
import { ChevronDown, SlidersHorizontal } from 'lucide-react'

export interface DocumentDisplaySettingsValues {
  showTags: boolean
}

interface DocumentDisplaySettingsProps {
  settings: DocumentDisplaySettingsValues
  onChange: (settings: DocumentDisplaySettingsValues) => void
}

interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label: string
  description?: string
}

function Toggle({ checked, onChange, label, description }: ToggleProps) {
  return (
    <label className="flex items-start gap-3 cursor-pointer group">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`
          relative inline-flex h-5 w-9 flex-shrink-0 mt-0.5 items-center rounded-full transition-colors
          ${checked ? 'bg-emerald-500' : 'bg-gray-200'}
        `}
      >
        <span
          className={`
            inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform
            ${checked ? 'translate-x-[18px]' : 'translate-x-0.5'}
          `}
        />
      </button>
      <div className="min-w-0">
        <div className="text-[13px] font-medium text-gray-900 leading-tight">{label}</div>
        {description && (
          <div className="text-[12px] text-gray-500 mt-0.5">{description}</div>
        )}
      </div>
    </label>
  )
}

export default function DocumentDisplaySettings({
  settings,
  onChange,
}: DocumentDisplaySettingsProps) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="border-b border-gray-100">
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 sm:px-6 py-2.5 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2 text-[13px] font-medium text-gray-600">
          <SlidersHorizontal className="h-4 w-4" />
          <span>Настройки отображения</span>
        </div>
        <ChevronDown
          className={`h-4 w-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {isOpen && (
        <div className="px-3 sm:px-6 pb-4 pt-1 bg-gray-50/50">
          <div className="space-y-3">
            <Toggle
              checked={settings.showTags}
              onChange={(checked) => onChange({ ...settings, showTags: checked })}
              label="Показывать тэги документа"
              description="Подтип («Анализ крови», «УЗИ»), специализация врача и область исследования"
            />
          </div>
        </div>
      )}
    </div>
  )
}
