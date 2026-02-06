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
  metadata: DocumentMetadata | null;
  page_count: number | null;
  clause_count: number | null;
  anomaly_count?: number;
  risk_score?: number | null;  // Overall risk score (1-10)
  risk_level?: 'Low' | 'Medium' | 'High' | 'Critical' | null;  // Document risk level
  processing_status?: string;  // processing, analyzing_anomalies, completed, failed
  created_at: string;
}

export interface DocumentMetadata {
  company?: string;
  company_name?: string;  // Backend uses company_name
  jurisdiction?: string;
  effective_date?: string;
  document_type?: string;
  governing_law?: string;
  version?: string;
  contact_email?: string;
  website?: string;
  last_updated?: string;
  extracted_at?: string;
}

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  metadata: DocumentMetadata | null;
  page_count: number | null;
  clause_count: number | null;
  anomaly_count: number;
  processing_status: string;  // processing, analyzing_anomalies, completed, failed
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
  severity: 'low' | 'medium' | 'high' | 'critical';
  explanation: string;
  prevalence: number;
  risk_flags: string[];
  created_at: string;
  // New fields for actionable advice
  consumer_impact?: string;
  recommendation?: string;
  risk_category?: string;
}

// Competitive Benchmark Types
export interface CompetitorInfo {
  company_name: string;
  avg_risk_score: number;
  notable_issues: string[];
}

export interface CompetitiveBenchmark {
  industry: string;
  industry_average_risk: number;
  percentile_rank: number; // 0=best, 100=worst
  risk_comparison: 'better' | 'similar' | 'worse';
  peer_count: number;
  better_alternatives: CompetitorInfo[];
  worse_alternatives: CompetitorInfo[];
  unique_risks: string[];
  missing_protections: string[];
  recommendations: string[];
  summary: string;
}

// Anomaly Report (full analysis response)
export interface AnomalyReport {
  document_id: string;
  company_name?: string;
  analysis_date: string;
  overall_risk_score: number;
  high_severity_alerts: RankedAnomaly[];
  medium_severity_alerts: RankedAnomaly[];
  low_severity_alerts: RankedAnomaly[];
  suppressed_alerts_count: number;
  total_anomalies_detected: number;
  total_alerts_shown: number;
  competitive_benchmark?: CompetitiveBenchmark;
}

export interface RankedAnomaly {
  clause_number?: string;
  clause_text: string;
  severity: string;
  risk_category: string;
  explanation?: string;
  consumer_impact?: string;
  recommendation?: string;
  ranking_score: number;
  is_compound_risk?: boolean;
  compound_risk_type?: string;
  compound_risk_name?: string;
}

export interface AnomalyStats {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface AnomalyListResponse {
  anomalies: Anomaly[];
  total: number;
  critical_risk_count: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  // Legacy support
  stats?: AnomalyStats;
}

// Query Types
export interface QueryRequest {
  document_id: string;
  question: string;
}

export interface Citation {
  clause_id: string;
  section: string;
  text: string;
  relevance_score: number;
  // Legacy support
  index?: number;
  clause?: string;
}

export interface QueryResponse {
  question: string;
  answer: string;
  citations: Citation[];
  sources?: string[];
  warnings?: string[];
  related_anomalies?: string[];
  // Legacy support
  confidence?: number;
}

// API Error Types
export interface APIError {
  detail: string | Array<{
    loc: string[];
    msg: string;
    type: string;
  }>;
}
