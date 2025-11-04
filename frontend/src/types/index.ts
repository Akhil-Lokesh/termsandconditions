// User Types
export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

// Document Types
export interface Document {
  id: string;
  user_id: string;
  filename: string;
  metadata: DocumentMetadata;
  page_count: number;
  clause_count: number;
  anomaly_count?: number;
  created_at: string;
}

export interface DocumentMetadata {
  company?: string;
  jurisdiction?: string;
  effective_date?: string;
  document_type?: string;
  version?: string;
}

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  metadata: DocumentMetadata;
  page_count: number;
  clause_count: number;
  anomaly_count: number;
  anomalies: Anomaly[];
  created_at: string;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  skip: number;
  limit: number;
}

// Anomaly Types
export interface Anomaly {
  id: string;
  document_id: string;
  clause_text: string;
  section: string;
  clause_number: string;
  severity: 'low' | 'medium' | 'high';
  explanation: string;
  prevalence: number;
  risk_flags: string[];
  created_at: string;
}

export interface AnomalyStats {
  total: number;
  high: number;
  medium: number;
  low: number;
}

export interface AnomalyListResponse {
  anomalies: Anomaly[];
  stats: AnomalyStats;
}

// Query Types
export interface QueryRequest {
  document_id: string;
  question: string;
}

export interface Citation {
  index: number;
  section: string;
  clause: string;
  text: string;
  relevance_score: number;
}

export interface QueryResponse {
  question: string;
  answer: string;
  citations: Citation[];
  confidence: number;
}

// API Error Types
export interface APIError {
  detail: string | Array<{
    loc: string[];
    msg: string;
    type: string;
  }>;
}
