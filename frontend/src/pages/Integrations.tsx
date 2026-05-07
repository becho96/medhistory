import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Plug, Trash2, Copy } from 'lucide-react'

import { mcpOAuthService } from '../services/mcpOAuth'

const MCP_PUBLIC_URL = import.meta.env.VITE_MCP_PUBLIC_URL || ''

export default function Integrations() {
  const queryClient = useQueryClient()

  const connections = useQuery({
    queryKey: ['mcp-connections'],
    queryFn: mcpOAuthService.listConnections,
  })

  const revoke = useMutation({
    mutationFn: mcpOAuthService.revokeConnection,
    onSuccess: () => {
      toast.success('Подключение отозвано')
      queryClient.invalidateQueries({ queryKey: ['mcp-connections'] })
    },
    onError: () => toast.error('Не удалось отозвать подключение'),
  })

  const mcpUrl = MCP_PUBLIC_URL ? `${MCP_PUBLIC_URL}/mcp` : ''

  const copyUrl = () => {
    if (!mcpUrl) return
    navigator.clipboard.writeText(mcpUrl)
    toast.success('URL скопирован')
  }

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-semibold text-gray-900 mb-2">Интеграции</h1>
      <p className="text-[15px] text-gray-500 mb-8">
        Подключайте внешние AI-сервисы к вашей медицинской истории через MCP.
      </p>

      {/* Setup card */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-8">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center flex-shrink-0">
            <Plug className="w-5 h-5 text-emerald-600" strokeWidth={2} />
          </div>
          <div className="flex-1">
            <h2 className="text-[17px] font-semibold text-gray-900 mb-1">Подключить Claude</h2>
            <p className="text-[14px] text-gray-500 mb-4">
              Откройте claude.ai → Settings → Connectors → Add custom connector. Вставьте URL
              ниже, OAuth-поля оставьте пустыми. После подключения вы вернётесь сюда для подтверждения.
            </p>
            {mcpUrl ? (
              <div className="flex gap-2 items-center">
                <code className="flex-1 px-3 py-2 bg-gray-50 rounded-lg text-[13px] font-mono text-gray-800 truncate">
                  {mcpUrl}
                </code>
                <button
                  type="button"
                  onClick={copyUrl}
                  className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                  title="Скопировать"
                >
                  <Copy className="w-4 h-4 text-gray-500" strokeWidth={2} />
                </button>
              </div>
            ) : (
              <p className="text-[13px] text-amber-700">
                MCP URL не настроен. Свяжитесь с администратором.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Active connections */}
      <h2 className="text-[17px] font-semibold text-gray-900 mb-4">Активные подключения</h2>

      {connections.isLoading && (
        <div className="text-[14px] text-gray-500">Загружаем...</div>
      )}

      {connections.data && connections.data.length === 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 p-8 text-center">
          <p className="text-[14px] text-gray-500">
            У вас пока нет активных подключений.
          </p>
        </div>
      )}

      {connections.data && connections.data.length > 0 && (
        <div className="space-y-3">
          {connections.data.map((conn) => (
            <div
              key={conn.client_id}
              className="bg-white rounded-2xl border border-gray-200 p-5 flex items-center gap-4"
            >
              <div className="flex-1 min-w-0">
                <div className="text-[15px] font-medium text-gray-900">
                  {conn.client_name || conn.client_id}
                </div>
                <div className="text-[13px] text-gray-500 mt-1">
                  Подключено {new Date(conn.issued_at).toLocaleString('ru-RU')}
                  {conn.expires_at && (
                    <> · истекает {new Date(conn.expires_at).toLocaleString('ru-RU')}</>
                  )}
                </div>
                <div className="text-[12px] text-gray-400 mt-1 font-mono truncate">
                  {conn.client_id}
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  if (confirm('Отозвать это подключение? Сервис потеряет доступ к вашим данным.')) {
                    revoke.mutate(conn.client_id)
                  }
                }}
                disabled={revoke.isPending}
                className="p-2 rounded-lg hover:bg-red-50 text-red-600 transition-colors disabled:opacity-50"
                title="Отозвать"
              >
                <Trash2 className="w-4 h-4" strokeWidth={2} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
