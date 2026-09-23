import axios from 'axios';

const CSRF_COOKIE = 'jobkler_csrf';

function readCookie(name: string): string | undefined {
  if (typeof document === 'undefined') return undefined;
  const prefix = `${name}=`;
  return document.cookie.split('; ').find((item) => item.startsWith(prefix))?.slice(prefix.length);
}

export const apiClient = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use(async (config) => {
  const method = (config.method || 'get').toLowerCase();
  if (!['post', 'put', 'patch', 'delete'].includes(method)) return config;

  let token = readCookie(CSRF_COOKIE);
  if (!token) {
    await apiClient.get('/auth/csrf');
    token = readCookie(CSRF_COOKIE);
  }
  if (token) config.headers.set('X-CSRF-Token', decodeURIComponent(token));
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error)) {
      const message = error.response?.data?.error;
      if (typeof message === 'string') error.message = message;
    }
    return Promise.reject(error);
  },
);
