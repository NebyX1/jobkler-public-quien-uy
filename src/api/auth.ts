import { apiClient } from './client';
import type {
  LoginRequest,
  LoginResponse,
  Verify2FARequest,
  Verify2FAResponse,
  User,
} from '../types';

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const res = await apiClient.post<LoginResponse>('/api/auth/login', data);
    return res.data;
  },

  verify2FA: async (
    code: string,
    pendingToken: string
  ): Promise<Verify2FAResponse> => {
    const res = await apiClient.post<Verify2FAResponse>(
      '/api/auth/verify-2fa',
      { code } satisfies Verify2FARequest,
      { headers: { Authorization: `Bearer ${pendingToken}` } }
    );
    return res.data;
  },

  me: async (): Promise<User> => {
    const res = await apiClient.get<{ user: User }>('/api/auth/me');
    return res.data.user;
  },
};
