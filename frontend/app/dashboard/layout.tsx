'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { Loading } from '@/components/ui';
import { useAuth } from '@/lib/auth';
import { ROLE_LABELS, type UserRole } from '@/lib/types';

/** Entradas del menu lateral y roles que pueden verlas. */
const NAV_ITEMS: { href: string; label: string; roles: UserRole[] }[] = [
  { href: '/dashboard', label: 'Resumen', roles: ['admin', 'receptionist', 'analyst', 'client'] },
  { href: '/dashboard/requests', label: 'Solicitudes', roles: ['admin', 'receptionist', 'analyst', 'client'] },
  { href: '/dashboard/clients', label: 'Clientes', roles: ['admin', 'receptionist'] },
  { href: '/dashboard/samples', label: 'Muestras', roles: ['admin', 'receptionist', 'analyst'] },
  { href: '/dashboard/users', label: 'Usuarios', roles: ['admin'] },
  { href: '/dashboard/notifications', label: 'Notificaciones', roles: ['admin', 'receptionist', 'analyst', 'client'] },
];

/**
 * Layout del panel.
 *
 * Actua como guarda de ruta: si no hay sesion activa redirige al login. Es una
 * proteccion de la interfaz, no de seguridad; quien realmente decide es el
 * backend, que valida el token y el rol en cada peticion.
 */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { session, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !session) {
      router.replace('/auth/login');
    }
  }, [loading, session, router]);

  if (loading) return <Loading message="Comprobando la sesión…" />;
  if (!session) return null; // Se esta redirigiendo al login.

  const visibleItems = NAV_ITEMS.filter((item) => item.roles.includes(session.role));

  const handleLogout = () => {
    logout();
    router.replace('/auth/login');
  };

  return (
    <div className="min-h-screen">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <Link href="/dashboard" className="text-lg font-bold text-brand-600">
            LabCloud
          </Link>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">
              {session.full_name}{' '}
              <span className="text-gray-400">· {ROLE_LABELS[session.role]}</span>
            </span>
            <button type="button" onClick={handleLogout} className="btn-secondary btn-sm">
              Salir
            </button>
          </div>
        </div>

        <nav className="mx-auto flex max-w-6xl gap-1 overflow-x-auto px-6">
          {visibleItems.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm transition ${
                  active
                    ? 'border-brand-600 font-medium text-brand-700'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
