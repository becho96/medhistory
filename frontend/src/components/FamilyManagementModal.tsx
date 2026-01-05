import { useState, useEffect } from 'react'
import { X, UserPlus, Users, User, Mail, Lock, Calendar, Trash2, Key, AlertCircle, CheckCircle, ChevronDown } from 'lucide-react'
import { familyService } from '../services/family'
import { useAuthStore } from '../stores/authStore'
import type { FamilyMember, FamilyMemberCreate, RelationType, FamilyOwnerInfo } from '../types'
import { RELATION_TYPE_LABELS } from '../types'

interface FamilyManagementModalProps {
  isOpen: boolean
  onClose: () => void
  onProfilesUpdated?: () => void
}

type TabType = 'members' | 'add' | 'invite' | 'credentials'

export default function FamilyManagementModal({ isOpen, onClose, onProfilesUpdated }: FamilyManagementModalProps) {
  const { user } = useAuthStore()
  const [activeTab, setActiveTab] = useState<TabType>('members')
  const [members, setMembers] = useState<FamilyMember[]>([])
  const [managedBy, setManagedBy] = useState<FamilyOwnerInfo[]>([])
  const [canDetach, setCanDetach] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Form states
  const [newMember, setNewMember] = useState<FamilyMemberCreate>({
    full_name: '',
    birth_date: '',
    relation_type: 'child',
    email: '',
  })

  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRelationType, setInviteRelationType] = useState<RelationType>('spouse')

  const [credentialsMemberId, setCredentialsMemberId] = useState<string | null>(null)
  const [credentialsEmail, setCredentialsEmail] = useState('')
  const [credentialsPassword, setCredentialsPassword] = useState('')

  useEffect(() => {
    if (isOpen) {
      loadFamilyInfo()
    }
  }, [isOpen])

  const loadFamilyInfo = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const info = await familyService.getMyFamilyInfo()
      setMembers(info.managing)
      setManagedBy(info.managed_by)
      setCanDetach(info.can_detach)
    } catch (err) {
      setError('Не удалось загрузить информацию о семье')
    } finally {
      setIsLoading(false)
    }
  }

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)

    if (!newMember.full_name.trim() || !newMember.birth_date) {
      setError('Заполните обязательные поля')
      return
    }

    try {
      setIsLoading(true)
      await familyService.createFamilyMember({
        ...newMember,
        email: newMember.email?.trim() || undefined,
      })
      setSuccess('Член семьи успешно добавлен')
      setNewMember({ full_name: '', birth_date: '', relation_type: 'child', email: '' })
      loadFamilyInfo()
      onProfilesUpdated?.()
      setTimeout(() => setActiveTab('members'), 1500)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Не удалось добавить члена семьи')
    } finally {
      setIsLoading(false)
    }
  }

  const handleInviteUser = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)

    if (!inviteEmail.trim()) {
      setError('Введите email пользователя')
      return
    }

    try {
      setIsLoading(true)
      await familyService.inviteExistingUser({
        email: inviteEmail,
        relation_type: inviteRelationType,
      })
      setSuccess('Пользователь успешно добавлен в семью')
      setInviteEmail('')
      loadFamilyInfo()
      onProfilesUpdated?.()
      setTimeout(() => setActiveTab('members'), 1500)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Не удалось добавить пользователя')
    } finally {
      setIsLoading(false)
    }
  }

  const handleRemoveMember = async (memberId: string) => {
    if (!confirm('Вы уверены, что хотите удалить этого члена семьи?')) return

    try {
      setIsLoading(true)
      setError(null)
      await familyService.removeFamilyMember(memberId)
      setSuccess('Член семьи удалён')
      loadFamilyInfo()
      onProfilesUpdated?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Не удалось удалить члена семьи')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSetCredentials = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!credentialsMemberId) return

    setError(null)
    setSuccess(null)

    if (!credentialsEmail.trim() || !credentialsPassword.trim()) {
      setError('Заполните email и пароль')
      return
    }

    if (credentialsPassword.length < 6) {
      setError('Пароль должен быть не менее 6 символов')
      return
    }

    try {
      setIsLoading(true)
      await familyService.setMemberCredentials(credentialsMemberId, {
        email: credentialsEmail,
        password: credentialsPassword,
      })
      setSuccess('Учетные данные установлены. Теперь пользователь может войти самостоятельно.')
      setCredentialsMemberId(null)
      setCredentialsEmail('')
      setCredentialsPassword('')
      loadFamilyInfo()
      onProfilesUpdated?.()
      setTimeout(() => setActiveTab('members'), 1500)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Не удалось установить учетные данные')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDetach = async (ownerId: string) => {
    if (!confirm('Вы уверены, что хотите отвязаться от этого профиля? Вы потеряете доступ к своим данным через этот аккаунт.')) return

    try {
      setIsLoading(true)
      setError(null)
      await familyService.detachFromFamily(ownerId)
      setSuccess('Вы успешно отвязались от семейного профиля')
      loadFamilyInfo()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Не удалось отвязаться')
    } finally {
      setIsLoading(false)
    }
  }

  const openCredentialsForm = (member: FamilyMember) => {
    setCredentialsMemberId(member.id)
    setCredentialsEmail(member.email || '')
    setCredentialsPassword('')
    setActiveTab('credentials')
  }

  if (!isOpen) return null

  const relationTypeOptions = Object.entries(RELATION_TYPE_LABELS).map(([value, label]) => ({
    value: value as RelationType,
    label,
  }))

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gradient-to-r from-[#4A90E2] to-[#3A7BC8]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
              <Users className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Семейные профили</h2>
              <p className="text-sm text-white/70">Управление членами семьи</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/20 transition-colors"
          >
            <X className="w-5 h-5 text-white" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-100">
          <button
            onClick={() => setActiveTab('members')}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === 'members' 
                ? 'text-blue-600 border-b-2 border-blue-600' 
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Users className="w-4 h-4 inline-block mr-2" />
            Члены семьи
          </button>
          <button
            onClick={() => setActiveTab('add')}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === 'add' 
                ? 'text-blue-600 border-b-2 border-blue-600' 
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <UserPlus className="w-4 h-4 inline-block mr-2" />
            Добавить
          </button>
          <button
            onClick={() => setActiveTab('invite')}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === 'invite' 
                ? 'text-blue-600 border-b-2 border-blue-600' 
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Mail className="w-4 h-4 inline-block mr-2" />
            Пригласить
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {/* Messages */}
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 flex items-center gap-2 text-sm text-red-700">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}
          {success && (
            <div className="mb-4 p-3 rounded-lg bg-green-50 border border-green-200 flex items-center gap-2 text-sm text-green-700">
              <CheckCircle className="w-4 h-4 flex-shrink-0" />
              {success}
            </div>
          )}

          {/* Members Tab */}
          {activeTab === 'members' && (
            <div className="space-y-4">
              {isLoading ? (
                <div className="text-center py-8 text-gray-500">Загрузка...</div>
              ) : members.length === 0 ? (
                <div className="text-center py-8">
                  <Users className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500">У вас пока нет добавленных членов семьи</p>
                  <button
                    onClick={() => setActiveTab('add')}
                    className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-sm"
                  >
                    Добавить члена семьи
                  </button>
                </div>
              ) : (
                <>
                  {members.map((member) => (
                    <div
                      key={member.id}
                      className="p-4 rounded-xl border border-gray-200 hover:border-gray-300 transition-colors"
                    >
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center flex-shrink-0">
                          <span className="text-white font-bold">
                            {member.full_name?.substring(0, 2).toUpperCase() || '??'}
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium text-gray-900 truncate">{member.full_name}</h4>
                          <p className="text-sm text-gray-500">{member.relation_type_display}</p>
                          {member.birth_date && (
                            <p className="text-xs text-gray-400 mt-1">
                              <Calendar className="w-3 h-3 inline-block mr-1" />
                              {new Date(member.birth_date).toLocaleDateString('ru-RU')}
                            </p>
                          )}
                          {member.email && (
                            <p className="text-xs text-gray-400 mt-1">
                              <Mail className="w-3 h-3 inline-block mr-1" />
                              {member.email}
                            </p>
                          )}
                          <div className="mt-2">
                            {member.has_credentials ? (
                              <span className="inline-flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full">
                                <CheckCircle className="w-3 h-3" />
                                Может войти самостоятельно
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded-full">
                                <AlertCircle className="w-3 h-3" />
                                Нет учетных данных
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex flex-col gap-2">
                          {!member.has_credentials && (
                            <button
                              onClick={() => openCredentialsForm(member)}
                              className="p-2 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors"
                              title="Установить email и пароль"
                            >
                              <Key className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            onClick={() => handleRemoveMember(member.id)}
                            className="p-2 rounded-lg bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
                            title="Удалить"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </>
              )}

              {/* Managed By Section */}
              {managedBy.length > 0 && (
                <div className="mt-6 pt-6 border-t border-gray-100">
                  <h4 className="text-sm font-medium text-gray-700 mb-3">Вашим профилем управляют:</h4>
                  {managedBy.map((owner) => (
                    <div
                      key={owner.id}
                      className="p-3 rounded-lg bg-gray-50 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gray-200 flex items-center justify-center">
                          <User className="w-4 h-4 text-gray-500" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-700">{owner.full_name || owner.email}</p>
                          <p className="text-xs text-gray-500">{owner.relation_type_display}</p>
                        </div>
                      </div>
                      {canDetach && (
                        <button
                          onClick={() => handleDetach(owner.id)}
                          className="text-xs text-red-600 hover:text-red-700 hover:underline"
                        >
                          Отвязаться
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Add Member Tab */}
          {activeTab === 'add' && (
            <form onSubmit={handleAddMember} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  ФИО <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={newMember.full_name}
                  onChange={(e) => setNewMember({ ...newMember, full_name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Иванов Иван Иванович"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Дата рождения <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  value={newMember.birth_date}
                  onChange={(e) => setNewMember({ ...newMember, birth_date: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Кем приходится <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <select
                    value={newMember.relation_type}
                    onChange={(e) => setNewMember({ ...newMember, relation_type: e.target.value as RelationType })}
                    className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white"
                  >
                    {relationTypeOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email (опционально)
                </label>
                <input
                  type="email"
                  value={newMember.email || ''}
                  onChange={(e) => setNewMember({ ...newMember, email: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="email@example.com"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Email можно добавить позже для самостоятельного входа
                </p>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 bg-gradient-to-r from-[#4A90E2] to-[#3A7BC8] text-white rounded-xl font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {isLoading ? 'Добавление...' : 'Добавить члена семьи'}
              </button>
            </form>
          )}

          {/* Invite Tab */}
          {activeTab === 'invite' && (
            <form onSubmit={handleInviteUser} className="space-y-4">
              <div className="p-4 rounded-lg bg-blue-50 border border-blue-100">
                <p className="text-sm text-blue-700">
                  Здесь вы можете добавить в семью пользователя, который уже зарегистрирован в системе.
                  Он сможет видеть вашу связь, но вы получите доступ к его медицинским данным.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email пользователя
                </label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="email@example.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Кем приходится
                </label>
                <div className="relative">
                  <select
                    value={inviteRelationType}
                    onChange={(e) => setInviteRelationType(e.target.value as RelationType)}
                    className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white"
                  >
                    {relationTypeOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 bg-gradient-to-r from-[#4A90E2] to-[#3A7BC8] text-white rounded-xl font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {isLoading ? 'Добавление...' : 'Добавить в семью'}
              </button>
            </form>
          )}

          {/* Credentials Tab */}
          {activeTab === 'credentials' && credentialsMemberId && (
            <form onSubmit={handleSetCredentials} className="space-y-4">
              <div className="p-4 rounded-lg bg-amber-50 border border-amber-100">
                <p className="text-sm text-amber-700">
                  После установки email и пароля этот член семьи сможет входить в систему самостоятельно 
                  и управлять своими медицинскими данными. В дальнейшем он сможет отвязать свой профиль от вашего аккаунта.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="email"
                    value={credentialsEmail}
                    onChange={(e) => setCredentialsEmail(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="email@example.com"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Пароль <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="password"
                    value={credentialsPassword}
                    onChange={(e) => setCredentialsPassword(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Минимум 6 символов"
                  />
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setCredentialsMemberId(null)
                    setActiveTab('members')
                  }}
                  className="flex-1 py-3 border border-gray-200 text-gray-700 rounded-xl font-medium hover:bg-gray-50 transition-colors"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex-1 py-3 bg-gradient-to-r from-[#4A90E2] to-[#3A7BC8] text-white rounded-xl font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {isLoading ? 'Сохранение...' : 'Сохранить'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}

