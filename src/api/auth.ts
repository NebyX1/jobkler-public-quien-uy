import { apiClient } from './client';
import type { AuthUser } from '../lib/auth';

export interface DemoAccount {
  key: string;
  name: string;
  description: string;
}

export interface AuthConfig {
  mode: 'demo' | 'fusionauth';
  demoEnabled: boolean;
  configured: boolean;
  aiSearchEnabled: boolean;
  demoBanner: boolean;
}

export const authApi = {
  config: async () => (await apiClient.get<AuthConfig>('/auth/config')).data,
  demoAccounts: async () => (await apiClient.get<{ accounts: DemoAccount[] }>('/auth/demo-accounts')).data.accounts,
  loginDemo: async (key: string) => (await apiClient.post<AuthUser>('/auth/demo-login', { key })).data,
  me: async () => (await apiClient.get<AuthUser>('/auth/me')).data,
  logout: async () => (await apiClient.post<{ ok: true }>('/auth/logout')).data,
};
