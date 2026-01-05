import api from '../lib/api'
import type { 
  FamilyMember, 
  FamilyMemberCreate, 
  FamilyMemberUpdate, 
  SetCredentials,
  MyFamilyInfo,
  InviteExistingUser,
  RelationType
} from '../types'

interface RelationTypeOption {
  value: RelationType
  label: string
}

export const familyService = {
  /**
   * Получить все доступные профили для переключения (включая свой)
   */
  async getAccessibleProfiles(): Promise<FamilyMember[]> {
    const response = await api.get<FamilyMember[]>('/family/profiles')
    return response.data
  },

  /**
   * Получить список членов семьи, которыми управляет текущий пользователь
   */
  async getFamilyMembers(): Promise<{ members: FamilyMember[]; total: number }> {
    const response = await api.get<{ members: FamilyMember[]; total: number }>('/family/members')
    return response.data
  },

  /**
   * Получить полную информацию о семейных связях
   */
  async getMyFamilyInfo(): Promise<MyFamilyInfo> {
    const response = await api.get<MyFamilyInfo>('/family/info')
    return response.data
  },

  /**
   * Получить список доступных типов отношений
   */
  async getRelationTypes(): Promise<RelationTypeOption[]> {
    const response = await api.get<RelationTypeOption[]>('/family/relation-types')
    return response.data
  },

  /**
   * Создать нового члена семьи
   */
  async createFamilyMember(data: FamilyMemberCreate): Promise<FamilyMember> {
    const response = await api.post<FamilyMember>('/family/members', data)
    return response.data
  },

  /**
   * Обновить информацию о члене семьи
   */
  async updateFamilyMember(memberId: string, data: FamilyMemberUpdate): Promise<FamilyMember> {
    const response = await api.put<FamilyMember>(`/family/members/${memberId}`, data)
    return response.data
  },

  /**
   * Установить email и пароль для члена семьи
   */
  async setMemberCredentials(memberId: string, credentials: SetCredentials): Promise<FamilyMember> {
    const response = await api.post<FamilyMember>(`/family/members/${memberId}/credentials`, credentials)
    return response.data
  },

  /**
   * Удалить члена семьи
   */
  async removeFamilyMember(memberId: string): Promise<void> {
    await api.delete(`/family/members/${memberId}`)
  },

  /**
   * Добавить существующего пользователя в семью
   */
  async inviteExistingUser(data: InviteExistingUser): Promise<FamilyMember> {
    const response = await api.post<FamilyMember>('/family/invite', data)
    return response.data
  },

  /**
   * Отвязаться от владельца профиля
   */
  async detachFromFamily(ownerId: string): Promise<void> {
    await api.post('/family/detach', { owner_id: ownerId })
  },

  /**
   * Проверить доступ к профилю
   */
  async checkProfileAccess(profileId: string): Promise<boolean> {
    const response = await api.get<{ has_access: boolean }>(`/family/check-access/${profileId}`)
    return response.data.has_access
  },
}

