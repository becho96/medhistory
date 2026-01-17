export type Gender = 'male' | 'female' | 'other'

export interface User {
  id: string
  email?: string
  full_name?: string
  birth_date?: string
  gender?: Gender
  is_active: boolean
  has_credentials?: boolean
  created_at: string
}

export interface UserUpdate {
  full_name?: string
  birth_date?: string
  gender?: Gender
}

// Типы семейных отношений
export type RelationType = 'parent' | 'child' | 'spouse' | 'grandparent' | 'grandchild' | 'sibling' | 'other'

export const RELATION_TYPE_LABELS: Record<RelationType, string> = {
  parent: 'Родитель',
  child: 'Ребенок',
  spouse: 'Супруг/супруга',
  grandparent: 'Бабушка/дедушка',
  grandchild: 'Внук/внучка',
  sibling: 'Брат/сестра',
  other: 'Другое',
}

export interface FamilyMember {
  id: string
  full_name: string
  birth_date?: string
  email?: string
  has_credentials: boolean
  relation_type: RelationType
  relation_type_display: string
  custom_relation?: string
  is_active: boolean
  created_at: string
  is_owner: boolean
}

export interface FamilyMemberCreate {
  full_name: string
  birth_date: string
  relation_type: RelationType
  custom_relation?: string
  email?: string
}

export interface FamilyMemberUpdate {
  full_name?: string
  birth_date?: string
  relation_type?: RelationType
  custom_relation?: string
}

export interface SetCredentials {
  email: string
  password: string
}

export interface FamilyOwnerInfo {
  id: string
  full_name?: string
  email?: string
  relation_type: RelationType
  relation_type_display: string
}

export interface MyFamilyInfo {
  managed_by: FamilyOwnerInfo[]
  managing: FamilyMember[]
  can_detach: boolean
}

export interface InviteExistingUser {
  email: string
  relation_type: RelationType
  custom_relation?: string
}

export interface Document {
  id: string
  user_id: string
  original_filename: string
  file_size: number
  file_type: string
  file_url: string
  document_type?: string
  specialty?: string
  document_date?: string
  patient_name?: string
  medical_facility?: string
  document_language?: string
  processing_status: 'pending' | 'processing' | 'completed' | 'failed'
  ai_confidence_score?: number
  mongodb_metadata_id?: string
  summary?: string
  created_at: string
  updated_at: string
}

export interface TimelineEvent {
  document_id: string
  date?: string
  document_type?: string
  document_subtype?: string
  specialty?: string
  title: string
  medical_facility?: string
  icon: string
  color: string
  file_url?: string
  original_filename?: string
  summary?: string
}

export interface TimelineResponse {
  total_count: number
  date_range?: {
    start: string
    end: string
  }
  events: TimelineEvent[]
}

export interface Report {
  id: string
  user_id: string
  report_type?: string
  filters_applied: string
  file_url: string
  file_size?: number
  created_at: string
}

export interface ReportFilters {
  specialty?: string
  document_type?: string
  date_from?: string
  date_to?: string
  medical_facility?: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  password: string
  full_name?: string
}

export interface AuthToken {
  access_token: string
  token_type: string
}

export interface InterpretationDocumentInfo {
  id: string
  original_filename: string
  document_date?: string
  document_type?: string
  document_subtype?: string
}

export interface Interpretation {
  id: string
  user_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  interpretation_text?: string
  error_message?: string
  created_at: string
  updated_at: string
  completed_at?: string
  documents: InterpretationDocumentInfo[]
}

export interface InterpretationCreate {
  document_ids: string[]
}

export interface InterpretationList {
  total: number
  items: Interpretation[]
}

