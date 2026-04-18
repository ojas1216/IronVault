import { api } from './client';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  role: string;
}

export interface RefreshResponse {
  access_token: string;
}

export const authApi = {
  login: (data: LoginRequest) =>
    api.post<LoginResponse>('/auth/login', data),

  refresh: (refreshToken: string) =>
    api.post<RefreshResponse>('/auth/refresh', { refresh_token: refreshToken }),

  logout: () =>
    api.post('/auth/logout'),

  me: () =>
    api.get<{ id: string; email: string; role: string; name: string }>('/auth/me'),
};
