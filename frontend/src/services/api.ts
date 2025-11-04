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
  Anomaly,
  APIError,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor: Add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getToken();
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor: Handle 401s
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<APIError>) => {
        if (error.response?.status === 401) {
          this.clearToken();
          window.location.href = '/login';
        }
        return Promise.reject(error);
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

    const response = await this.client.post<DocumentUploadResponse>('/documents', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  async getDocuments(skip = 0, limit = 10): Promise<DocumentListResponse> {
    const response = await this.client.get<DocumentListResponse>('/documents', {
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
    const response = await this.client.post<QueryResponse>('/query', data);
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

  async getAnomaly(documentId: string, anomalyId: string): Promise<Anomaly> {
    const response = await this.client.get<Anomaly>(`/anomalies/${documentId}/${anomalyId}`);
    return response.data;
  }
}

export const api = new APIClient();
export default api;
