export interface User {
  id: string
  email: string
  full_name?: string
  is_active: boolean
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

