import { api } from '../lib/api'

export interface ConsentInfo {
  client_id: string
  client_name: string | null
  client_uri: string | null
  scopes: string[]
}

export interface ConsentDecision {
  redirect_url: string
}

export interface McpConnection {
  client_id: string
  client_name: string | null
  issued_at: string
  expires_at: string | null
  scopes: string[]
}

export const mcpOAuthService = {
  async getConsentInfo(req: string): Promise<ConsentInfo> {
    const response = await api.get<ConsentInfo>('/oauth/consent/info', { params: { req } })
    return response.data
  },

  async submitConsent(req: string, decision: 'approve' | 'deny'): Promise<ConsentDecision> {
    const response = await api.post<ConsentDecision>('/oauth/consent/decision', { req, decision })
    return response.data
  },

  async listConnections(): Promise<McpConnection[]> {
    const response = await api.get<McpConnection[]>('/mcp/connections')
    return response.data
  },

  async revokeConnection(clientId: string): Promise<void> {
    await api.delete(`/mcp/connections/${clientId}`)
  },
}
