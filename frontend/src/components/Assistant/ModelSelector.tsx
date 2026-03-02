import { useEffect, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { fetchAvailableModels, type ModelConfig } from '../../services/assistant'

interface Props {
  value: ModelConfig
  onChange: (cfg: ModelConfig) => void
  disabled?: boolean
}

const STORAGE_KEY = 'assistant_model_config'

const FALLBACK_MODELS = {
  anthropic: [
    { id: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6 (рекомендуется)' },
    { id: 'claude-opus-4-6',   label: 'Claude Opus 4.6 (максимум)' },
    { id: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5 (быстрый)' },
  ],
  openrouter: [
    { id: 'google/gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
  ],
}

export function loadSavedModelConfig(): ModelConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return { provider: 'anthropic', model_id: 'claude-sonnet-4-6' }
}

export default function ModelSelector({ value, onChange, disabled }: Props) {
  const [models, setModels] = useState<Record<string, { id: string; label: string }[]>>(FALLBACK_MODELS)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    fetchAvailableModels()
      .then(setModels)
      .catch(() => {/* use fallback */})
  }, [])

  const allOptions = Object.entries(models).flatMap(([provider, list]) =>
    list.map((m) => ({ provider, ...m }))
  )

  const currentLabel =
    allOptions.find((o) => o.provider === value.provider && o.id === value.model_id)?.label
    ?? `${value.provider} / ${value.model_id}`

  const select = (provider: string, id: string) => {
    const cfg: ModelConfig = { provider, model_id: id }
    onChange(cfg)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg))
    setOpen(false)
  }

  return (
    <div className="relative">
      <button
        onClick={() => !disabled && setOpen((o) => !o)}
        disabled={disabled}
        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border transition-colors
          ${disabled
            ? 'bg-gray-50 text-gray-400 border-gray-200 cursor-not-allowed'
            : 'bg-white text-gray-700 border-gray-200 hover:border-gray-300 hover:bg-gray-50'
          }`}
      >
        <span className="max-w-[140px] truncate">{currentLabel}</span>
        <ChevronDown className="w-3 h-3 flex-shrink-0" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-20 w-64 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
            {Object.entries(models).map(([provider, list]) => (
              <div key={provider}>
                <div className="px-3 py-2 text-[10px] font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-100 bg-gray-50">
                  {provider === 'anthropic' ? 'Anthropic Claude' : 'OpenRouter'}
                </div>
                {list.map((m) => {
                  const isActive = value.provider === provider && value.model_id === m.id
                  return (
                    <button
                      key={m.id}
                      onClick={() => select(provider, m.id)}
                      className={`w-full text-left px-3 py-2.5 text-sm transition-colors
                        ${isActive ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700 hover:bg-gray-50'}`}
                    >
                      {m.label}
                    </button>
                  )
                })}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
