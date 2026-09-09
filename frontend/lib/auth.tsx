'use client';

/**
 * Contexto de sesion.
 *
 * Guarda quien ha iniciado sesion y lo pone a disposicion de toda la aplicacion
 * mediante el hook `useAuth()`, para no tener que leer `localStorage` desde
 * cada pantalla.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { authService, clearSession, readSession, saveSession } from './api';
import type { Session, UserRole } from './types';

interface AuthContextValue {
  /** Sesion activa, o `null` si nadie ha iniciado sesion. */
  session: Session | null;
  /** `true` mientras se recupera la sesion guardada al cargar la pagina. */
  loading: boolean;
  login: (email: string, password: string) => Promise<Session>;
  logout: () => void;
  /** Indica si el usuario actual tiene alguno de los roles indicados. */
  hasRole: (...roles: UserRole[]) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  // La sesion se lee dentro de `useEffect` porque `localStorage` solo existe en
  // el navegador; hacerlo durante el renderizado romperia el servidor de Next.
  useEffect(() => {
    setSession(readSession());
    setLoading(false);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await authService.login(email, password);
    saveSession(data);
    setSession(data);
    return data;
  }, []);

  const logout = useCallback(() => {
    clearSession();
    setSession(null);
  }, []);

  const hasRole = useCallback(
    (...roles: UserRole[]) => (session ? roles.includes(session.role) : false),
    [session],
  );

  const value = useMemo(
    () => ({ session, loading, login, logout, hasRole }),
    [session, loading, login, logout, hasRole],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Devuelve el contexto de sesion. Debe usarse dentro de `<AuthProvider>`. */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth debe usarse dentro de <AuthProvider>');
  }
  return context;
}
