import axios, { AxiosError, AxiosInstance } from 'axios';
import type {
  User,
  LoginRequest,
  SignupRequest,
  AuthResponse,
  Document,
  DocumentUploadResponse,
  DocumentListResponse,
  QueryRequest,
  QueryResponse,
  AnomalyListResponse,
  AnomalyReport,
  Anomaly,
  APIError,
  FeedbackPayload,
  FeedbackResponse,
} from '@/types';

// Determine API URL based on environment
function getApiBaseUrl(): string {
  // Check for explicitly set environment variable first
  const envUrl = import.meta.env.VITE_API_URL;
  
  if (envUrl && envUrl.trim() !== '') {
    // Ensure HTTPS in production
    const url = envUrl.trim();
    if (import.meta.env.PROD && url.startsWith('http://')) {
      return url.replace('http://', 'https://') + '/api/v1';
    }
    return url + '/api/v1';
  }
  
  // Production default - ALWAYS use HTTPS
  if (import.meta.env.PROD) {
    return 'https://termsandconditions-production.up.railway.app/api/v1';
  }
  
  // Development default
  return 'http://localhost:8000/api/v1';
}

const API_BASE_URL = getApiBaseUrl();

// Log the URL in development for debugging
if (import.meta.env.DEV) {
  console.log('API Base URL:', API_BASE_URL);
}

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 60000, // 60 second timeout
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor: Add auth token and handle FormData
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getToken();
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        
        // If sending FormData, remove Content-Type so browser sets it with boundary
        if (config.data instanceof FormData && config.headers) {
          delete config.headers['Content-Type'];
        }
        
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor: Handle errors with user-friendly messages
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<APIError>) => {
        // Extract the backend's `detail` once. FastAPI returns either a string
        // (HTTPException) or an array of {msg} (422 validation errors).
        const rawDetail = error.response?.data?.detail;
        const backendDetail =
          typeof rawDetail === 'string'
            ? rawDetail
            : Array.isArray(rawDetail)
              ? rawDetail.map((e) => e.msg).join(', ')
              : undefined;

        const url = error.config?.url ?? '';
        const isAuthEndpoint =
          url.includes('/auth/login') || url.includes('/auth/signup');

        // User-friendly error messages
        let message = 'An unexpected error occurred';

        if (error.response) {
          // Server responded with error
          switch (error.response.status) {
            case 400:
            case 409:
            case 422:
              // Surface the backend's validation/business message verbatim.
              message = backendDetail || 'Invalid request. Please check your input.';
              break;
            case 401:
              if (isAuthEndpoint) {
                // A 401 from login/signup means bad credentials — NOT an expired
                // session. Show the real reason and do NOT trigger a global logout.
                message = backendDetail || 'Incorrect email or password.';
              } else {
                message = 'Please log in to continue.';
                this.clearToken();
                window.dispatchEvent(new Event('auth:logout'));
              }
              break;
            case 403:
              message = backendDetail || 'You do not have permission to perform this action.';
              break;
            case 404:
              message = backendDetail || 'The requested resource was not found.';
              break;
            case 413:
              message = 'File is too large. Maximum size is 10MB.';
              break;
            case 429:
              message = 'Too many requests. Please try again later.';
              break;
            case 500:
              message = 'Server error. Please try again later.';
              break;
            case 503:
              message = 'Service temporarily unavailable. Please try again in a few minutes.';
              break;
            default:
              message = backendDetail || message;
          }
        } else if (error.request) {
          // Request made but no response
          message = 'Cannot connect to server. Please check your internet connection.';
        } else {
          // Error in request setup
          message = error.message;
        }

        // Friendly error: `message` is always set; `detail` carries the raw backend
        // detail for callers that want it. NOTE: there is no `.response` field —
        // consumers must read `.message` (or `.detail`), not `error.response.data.detail`.
        const friendlyError = {
          message,
          detail: backendDetail,
          status: error.response?.status,
          originalError: error,
        };

        return Promise.reject(friendlyError);
      }
    );
  }

  // Token management
  getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  private setToken(token: string): void {
    localStorage.setItem('access_token', token);
  }

  clearToken(): void {
    localStorage.removeItem('access_token');
  }

  // Authentication
  async signup(data: SignupRequest): Promise<User> {
    const response = await this.client.post<User>('/auth/signup', data);
    return response.data;
  }

  async login(data: LoginRequest): Promise<AuthResponse> {
    // Login uses form data
    const formData = new URLSearchParams();
    formData.append('username', data.username);
    formData.append('password', data.password);

    const response = await this.client.post<AuthResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    this.setToken(response.data.access_token);
    return response.data;
  }

  logout(): void {
    this.clearToken();
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/auth/me');
    return response.data;
  }

  // Documents
  async uploadDocument(file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    // FormData Content-Type is handled automatically by request interceptor
    const response = await this.client.post<DocumentUploadResponse>('/documents/', formData, {
      timeout: 120000, // 2 minutes for document processing
    });

    return response.data;
  }

  async uploadText(text: string, title?: string): Promise<DocumentUploadResponse> {
    const response = await this.client.post<DocumentUploadResponse>('/documents/text', {
      text,
      title,
    }, {
      timeout: 120000, // 2 minutes for text processing
    });

    return response.data;
  }

  async getDocuments(skip = 0, limit = 10): Promise<DocumentListResponse> {
    const response = await this.client.get<DocumentListResponse>('/documents/', {
      params: { skip, limit },
    });
    return response.data;
  }

  async getDocument(id: string): Promise<Document> {
    const response = await this.client.get<Document>(`/documents/${id}`);
    return response.data;
  }

  async deleteDocument(id: string): Promise<void> {
    await this.client.delete(`/documents/${id}`);
  }

  // Queries
  async queryDocument(data: QueryRequest): Promise<QueryResponse> {
    const response = await this.client.post<QueryResponse>('/query/', data);
    return response.data;
  }

  // Anomalies
  async getAnomalies(
    documentId: string,
    params?: {
      severity?: string;
      section?: string;
      skip?: number;
      limit?: number;
    }
  ): Promise<AnomalyListResponse> {
    const response = await this.client.get<AnomalyListResponse>(`/anomalies/${documentId}`, {
      params,
    });
    return response.data;
  }

  async getAnomaly(anomalyId: string): Promise<Anomaly> {
    const response = await this.client.get<Anomaly>(`/anomalies/detail/${anomalyId}`);
    return response.data;
  }

  async reanalyzeDocument(documentId: string): Promise<AnomalyListResponse> {
    const response = await this.client.post<AnomalyListResponse>(`/anomalies/reanalyze/${documentId}`);
    return response.data;
  }

  // Get full anomaly report with competitive benchmark
  async getAnomalyReport(documentId: string): Promise<AnomalyReport> {
    const response = await this.client.get<AnomalyReport>(`/anomalies/report/${documentId}`, {
      timeout: 120000, // 2 minutes for full analysis
    });
    return response.data;
  }

  // Submit user feedback on a detected anomaly (Layer 5 — active learning)
  async submitFeedback(
    anomalyId: string,
    payload: FeedbackPayload
  ): Promise<FeedbackResponse> {
    const response = await this.client.post<FeedbackResponse>(
      `/anomalies/${anomalyId}/feedback`,
      payload
    );
    return response.data;
  }
}

export const api = new APIClient();
export default api;
