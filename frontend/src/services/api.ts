import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { AuthResponse, LoginCredentials, Train, Section, SectionStatus, Position, Conflict, PerformanceMetrics } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem('access_token');
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling and token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        // Handle 401 unauthorized errors
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          
          // Clear token and redirect to login
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          
          // Only redirect if not already on login page
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
          
          return Promise.reject(error);
        }

        // Handle 403 forbidden errors
        if (error.response?.status === 403) {
          console.error('Access forbidden:', error.response.data);
        }

        // Don't show error notification for cancelled requests
        if (axios.isCancel(error)) {
          return Promise.reject(error);
        }

        return Promise.reject(error);
      }
    );
  }

  // Authentication endpoints
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>('/auth/login', credentials);
    return response.data;
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout');
  }

  async getCurrentUser() {
    const response = await this.client.get('/auth/me');
    return response.data;
  }

  // Train endpoints
  async getTrains(): Promise<Train[]> {
    const response = await this.client.get<Train[]>('/trains');
    return response.data;
  }

  async getTrain(id: number): Promise<Train> {
    const response = await this.client.get<Train>(`/trains/${id}`);
    return response.data;
  }

  async updateTrainPosition(position: Partial<Position>): Promise<void> {
    await this.client.post('/trains/position', position);
  }

  // Section endpoints
  async getSections(): Promise<Section[]> {
    const response = await this.client.get<Section[]>('/sections');
    return response.data;
  }

  async getSectionStatus(sectionId?: number): Promise<SectionStatus[]> {
    const url = sectionId ? `/sections/${sectionId}/status` : '/sections/status';
    const response = await this.client.get<any>(url);
    return sectionId ? [response.data] : response.data.sections;
  }

  // Conflict endpoints
  async getConflicts(hours: number = 24): Promise<Conflict[]> {
    const response = await this.client.get<any>('/conflicts/history', {
      params: { hours }
    });
    // Extract conflicts array from wrapped response
    return response.data?.data?.conflicts || response.data?.conflicts || response.data || [];
  }

  async getConflictStatus() {
    const response = await this.client.get('/conflicts/status');
    return response.data;
  }

  async manualConflictDetection() {
    const response = await this.client.post('/conflicts/detect');
    return response.data;
  }

  // Performance endpoints
  async getPerformanceMetrics(): Promise<PerformanceMetrics> {
    const response = await this.client.get<PerformanceMetrics>('/performance');
    return response.data;
  }

  async getHealthStatus() {
    const response = await this.client.get('/health');
    return response.data;
  }

  // Generic GET method
  async get<T = any>(url: string, params?: any): Promise<T> {
    const response = await this.client.get<T>(url, { params });
    return response.data;
  }

  // Generic POST method
  async post<T = any>(url: string, data?: any): Promise<T> {
    const response = await this.client.post<T>(url, data);
    return response.data;
  }

  // Generic PUT method
  async put<T = any>(url: string, data?: any): Promise<T> {
    const response = await this.client.put<T>(url, data);
    return response.data;
  }

  // Generic DELETE method
  async delete<T = any>(url: string): Promise<T> {
    const response = await this.client.delete<T>(url);
    return response.data;
  }
}

export const apiService = new ApiService();
export default apiService;
