import type { Metadata } from 'next';

import { AuthProvider } from '@/lib/auth';

import './globals.css';

export const metadata: Metadata = {
  title: 'LabCloud · Gestión de análisis de laboratorio',
  description:
    'Plataforma para registrar muestras, gestionar solicitudes de análisis y consultar resultados.',
};

/**
 * Layout raiz de la aplicacion.
 *
 * Envuelve todas las paginas en `AuthProvider` para que cualquiera de ellas
 * pueda consultar la sesion activa con `useAuth()`.
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
