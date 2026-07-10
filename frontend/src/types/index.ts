export type Gender = 'male' | 'female' | 'other'

export type SubscriptionTier = 'free' | 'pro'

export interface User {
  id: string
  email?: string
  full_name?: string
  birth_date?: string
  gender?: Gender
  is_active: boolean
  has_credentials?: boolean
  subscription_tier: SubscriptionTier
  pro_expires_at?: string | null
  is_admin: boolean
  created_at: string
}

export interface SubscriptionInfo {
  tier: SubscriptionTier
  limit: number
  used: number
  remaining: number
  pro_expires_at?: string | null
  billing_owner_id: string
  is_billing_owner: boolean
}

export interface ActivatePromoCodeResponse {
  subscription: SubscriptionInfo
  duration_days: number
  activated_until: string
}

export interface PromoCode {
  id: string
  code: string
  duration_days: number
  max_activations: number
  activations_count: number
  expires_at?: string | null
  is_active: boolean
  comment?: string | null
  created_at: string
}

export interface PromoCodeCreate {
  code?: string
  duration_days: number
  max_activations: number
  expires_at?: string | null
  comment?: string | null
}

export interface AdminUserListItem {
  id: string
  email?: string | null
  full_name?: string | null
  subscription_tier: SubscriptionTier
  pro_expires_at?: string | null
  is_admin: boolean
  is_active: boolean
  created_at: string
  documents_count: number
}

export interface AdminStats {
  total_users: number
  pro_users: number
  active_promocodes: number
  activations_this_month: number
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

export interface FamilyInvite {
  id: string
  owner_id: string
  owner_full_name?: string
  owner_email?: string
  relation_type: RelationType
  relation_type_display: string
  custom_relation?: string
  created_at: string
}

export interface Document {
  id: string
  user_id: string
  original_filename: string
  file_size: number
  file_type: string
  file_url: string
  document_type?: string
  document_subtype?: string
  specialty?: string
  research_area?: string
  document_date?: string
  patient_name?: string
  medical_facility?: string
  document_language?: string
  processing_status: 'pending' | 'processing' | 'completed' | 'failed'
  ai_confidence_score?: number
  mongodb_metadata_id?: string
  summary?: string
  orders_summary?: DocumentOrdersSummary | null
  created_at: string
  updated_at: string
}

export interface DocumentOrderStatus {
  order_index: number
  title: string
  order_type?: string | null
  target_document_type?: string | null
  target_document_subtype?: string | null
  target_research_area?: string | null
  status: 'pending' | 'completed' | 'not_required' | 'incorrect'
  status_source: 'auto' | 'manual'
  is_active: boolean
  matched_document_id?: string | null
  matched_document_date?: string | null
  matched_document_title?: string | null
}

export interface DocumentOrdersSummary {
  total: number
  completed: number
  pending: number
  dismissed: number
  items: DocumentOrderStatus[]
}

export type ReminderKind = 'follow_up_appointment' | 'referral_research' | 'referral_specialist'
export type ReminderStatus = 'active' | 'done' | 'dismissed'
export type ReminderUrgency = 'overdue' | 'urgent' | 'soon' | 'planned' | 'no_date'

export interface Reminder {
  id: string
  origin: 'auto' | 'manual'
  kind: ReminderKind
  title: string
  due_date?: string | null
  urgency_level: ReminderUrgency
  days_left?: number | null
  status: ReminderStatus
  target_document_type?: string | null
  target_specialty?: string | null
  note?: string | null
  source_document_id?: string | null
  source_document_title?: string | null
  source_document_date?: string | null
  source_specialty?: string | null
  completed_document_id?: string | null
  created_at?: string | null
}

export interface DocumentExtractedTable {
  title?: string | null
  columns?: string[]
  rows?: Array<Record<string, unknown>>
}

export interface DocumentLabResult {
  test_name?: string | null
  value?: string | null
  unit?: string | null
  reference_range?: string | null
  flag?: string | null
}

export interface DocumentContent {
  document_id: string
  summary?: string | null
  full_text?: string | null
  full_text_source?: string | null
  tables: DocumentExtractedTable[]
  lab_results: DocumentLabResult[]
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
  consents: {
    terms_and_privacy: string
    special_category: string
  }
  signup_utm?: Record<string, string>
  interview_opt_in?: boolean
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

// Health Events Types
export type ParameterType = 'number' | 'scale' | 'text' | 'boolean'

export interface ParameterConfig {
  unit?: string
  min?: number
  max?: number
  step?: number
  placeholder?: string
  pattern?: string
  options?: Array<{ value: string; label: string }>
  labels?: Record<number, string>
}

export interface ParameterDefinition {
  key: string
  label_ru: string
  type: ParameterType
  config: ParameterConfig
  is_primary: boolean
  sort_order: number
}

export interface HealthEvent {
  id: string
  user_id: string
  event_datetime: string
  parameters: Record<string, any>
  tags: string[]
  notes?: string
  created_at: string
  updated_at: string
}

export interface HealthEventCreate {
  event_datetime: string
  parameters: Record<string, any>
  tags: string[]
  notes?: string
}

export interface HealthEventsListResponse {
  total: number
  events: HealthEvent[]
}
