/**
 * Cliente HTTP de la API de LabCloud.
 *
 * Centraliza la URL base, adjunta el token JWT en cada peticion y traduce los
 * errores de axios a mensajes legibles. Las pantallas solo llaman a los
 * servicios de este archivo; ninguna construye una URL por su cuenta.
 */

import axios, { AxiosError, AxiosInstance } from 'axios';

import type {
  AnalysisRequest,
  Client,
  Notification,
  RequestStatus,
  Result,
  Sample,
  Session,
  User,
  UserRole,
} from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** Clave con la que se guarda la sesion en el navegador. */
export const STORAGE_KEY = 'labcloud_session';

/**
 * Lee la sesion guardada.
 *
 * Devuelve `null` en el servidor: las paginas de Next.js tambien se renderizan
 * en Node, donde `localStorage` no existe y su uso directo lanzaria un error.
 */
export function readSession(): Session | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    // Datos corruptos o almacenamiento bloqueado: se trata como "sin sesion".
    return null;
  }
}

/** Guarda la sesion tras un inicio de sesion correcto. */
export function saveSession(session: Session): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

/** Borra la sesion guardada. */
export function clearSession(): void {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(STORAGE_KEY);
}

const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Adjunta el token a cada peticion saliente.
api.interceptors.request.use((config) => {
  const session = readSession();
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  return config;
});

// Si el token caduca o deja de ser valido, se cierra la sesion y se vuelve al
// login. Se comprueba la ruta actual para no entrar en un bucle de redirecciones.
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      clearSession();
      if (!window.location.pathname.startsWith('/auth/')) {
        window.location.href = '/auth/login';
      }
    }
    return Promise.reject(error);
  },
);

/**
 * Extrae un mensaje legible de un error de la API.
 *
 * El backend responde `{"detail": "..."}` en los errores de negocio y una lista
 * de problemas de validacion cuando Pydantic rechaza el cuerpo de la peticion.
 */
export function getErrorMessage(error: unknown, fallback = 'Ha ocurrido un error'): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      return detail.map((item: { msg?: string }) => item.msg ?? '').join('. ') || fallback;
    }
    if (!error.response) {
      return 'No se pudo conectar con el servidor. ¿Está el backend en marcha?';
    }
  }
  return fallback;
}

export default api;

// ---------------------------------------------------------------------------
// Servicios por recurso
// ---------------------------------------------------------------------------

export const authService = {
  login: (email: string, password: string) =>
    api.post<Session>('/api/auth/login', { email, password }),
  register: (email: string, password: string, full_name: string) =>
    api.post<User>('/api/auth/register', { email, password, full_name }),
  me: () => api.get<User>('/api/auth/me'),
};

export const userService = {
  getAll: () => api.get<User[]>('/api/users/'),
  getAnalysts: () => api.get<User[]>('/api/users/analysts'),
  create: (data: { email: string; password: string; full_name: string; role: UserRole }) =>
    api.post<User>('/api/users/', data),
  setRole: (id: number, role: UserRole) => api.put<User>(`/api/users/${id}/role`, { role }),
  setActive: (id: number, isActive: boolean) =>
    api.put<User>(`/api/users/${id}/active`, { is_active: isActive }),
};

export const clientService = {
  getAll: () => api.get<Client[]>('/api/clients/'),
  getById: (id: number) => api.get<Client>(`/api/clients/${id}`),
  create: (data: {
    name: string;
    email: string;
    phone?: string;
    address?: string;
    user_id?: number | null;
  }) => api.post<Client>('/api/clients/', data),
  update: (id: number, data: Partial<Client>) => api.put<Client>(`/api/clients/${id}`, data),
  remove: (id: number) => api.delete(`/api/clients/${id}`),
};

export const sampleService = {
  getAll: () => api.get<Sample[]>('/api/samples/'),
  getByClient: (clientId: number) => api.get<Sample[]>(`/api/samples/client/${clientId}`),
  create: (data: { sample_type: string; description?: string; client_id: number }) =>
    api.post<Sample>('/api/samples/', data),
};

export const requestService = {
  getAll: () => api.get<AnalysisRequest[]>('/api/requests/'),
  getMine: () => api.get<AnalysisRequest[]>('/api/requests/mine'),
  getById: (id: number) => api.get<AnalysisRequest>(`/api/requests/${id}`),
  getByStatus: (status: RequestStatus) =>
    api.get<AnalysisRequest[]>(`/api/requests/status/${status}`),
  create: (data: { client_id: number; sample_id: number; test_type: string }) =>
    api.post<AnalysisRequest>('/api/requests/', data),
  assignAnalyst: (id: number, analystId: number) =>
    api.put<AnalysisRequest>(`/api/requests/${id}/analyst`, { analyst_id: analystId }),
  changeStatus: (id: number, status: RequestStatus) =>
    api.put<AnalysisRequest>(`/api/requests/${id}/status`, { status }),
};

export const resultService = {
  getAll: () => api.get<Result[]>('/api/results/'),
  getByRequest: (requestId: number) => api.get<Result>(`/api/results/request/${requestId}`),
  create: (data: { request_id: number; result_value: string; result_notes?: string }) =>
    api.post<Result>('/api/results/', data),
};

export const notificationService = {
  getMine: () => api.get<Notification[]>('/api/notifications/mine'),
  markAsRead: (id: number) => api.put<Notification>(`/api/notifications/${id}/read`),
};
