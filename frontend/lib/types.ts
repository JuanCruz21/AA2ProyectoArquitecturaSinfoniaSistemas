/**
 * Tipos compartidos del frontend.
 *
 * Reflejan los esquemas Pydantic del backend. Tenerlos escritos permite que
 * TypeScript avise en tiempo de compilacion si una pantalla usa un campo que la
 * API no devuelve, en lugar de fallar en el navegador.
 */

export type UserRole = 'admin' | 'receptionist' | 'analyst' | 'client';

export type RequestStatus = 'pending' | 'in_analysis' | 'completed' | 'cancelled';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Session {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_id: number;
  email: string;
  full_name: string;
  role: UserRole;
}

export interface Client {
  id: number;
  name: string;
  email: string;
  phone: string;
  address: string;
  user_id: number | null;
  created_at: string;
}

export interface Sample {
  id: number;
  sample_code: string;
  sample_type: string;
  description: string;
  client_id: number;
  received_date: string;
  created_at: string;
}

export interface AnalysisRequest {
  id: number;
  request_code: string;
  client_id: number;
  sample_id: number;
  test_type: string;
  status: RequestStatus;
  assigned_analyst_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface Result {
  id: number;
  request_id: number;
  analyst_id: number;
  result_value: string;
  result_notes: string;
  created_at: string;
}

export interface Notification {
  id: number;
  user_id: number;
  request_id: number;
  message: string;
  is_read: boolean;
  created_at: string;
}

/** Etiquetas en espanol de cada rol, para mostrarlas en la interfaz. */
export const ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Administrador',
  receptionist: 'Recepcionista',
  analyst: 'Analista',
  client: 'Cliente',
};

/** Etiquetas en espanol de cada estado de solicitud. */
export const STATUS_LABELS: Record<RequestStatus, string> = {
  pending: 'Pendiente',
  in_analysis: 'En análisis',
  completed: 'Completada',
  cancelled: 'Cancelada',
};

/** Clases de Tailwind con el color asociado a cada estado. */
export const STATUS_STYLES: Record<RequestStatus, string> = {
  pending: 'bg-amber-100 text-amber-800',
  in_analysis: 'bg-blue-100 text-blue-800',
  completed: 'bg-emerald-100 text-emerald-800',
  cancelled: 'bg-gray-200 text-gray-700',
};
