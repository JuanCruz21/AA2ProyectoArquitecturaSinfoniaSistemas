'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { ErrorAlert, Field } from '@/components/ui';
import { getErrorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';

/** Pantalla de inicio de sesion. */
export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      router.push('/dashboard');
    } catch (err) {
      setError(getErrorMessage(err, 'No se pudo iniciar sesión'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-md rounded-lg border border-gray-200 bg-white p-8 shadow-sm">
        <h1 className="mb-1 text-2xl font-bold text-gray-900">Iniciar sesión</h1>
        <p className="mb-6 text-sm text-gray-600">Acceda con su cuenta de LabCloud.</p>

        <ErrorAlert message={error} />

        <form onSubmit={handleSubmit} className="space-y-4">
          <Field label="Correo electrónico" htmlFor="email">
            <input
              id="email"
              type="email"
              autoComplete="email"
              className="form-input"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="usuario@labcloud.com"
              required
            />
          </Field>

          <Field label="Contraseña" htmlFor="password">
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              className="form-input"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              required
            />
          </Field>

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? 'Entrando…' : 'Entrar'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-600">
          ¿No tiene cuenta?{' '}
          <Link href="/auth/register" className="font-medium text-brand-600 hover:underline">
            Regístrese
          </Link>
        </p>

        <div className="mt-6 rounded-md bg-gray-50 p-4 text-xs text-gray-600">
          <p className="mb-1 font-semibold text-gray-700">
            Cuentas de prueba (contraseña: password123)
          </p>
          <ul className="space-y-0.5">
            <li>admin@labcloud.com — administrador</li>
            <li>recepcion@labcloud.com — recepcionista</li>
            <li>analista@labcloud.com — analista</li>
            <li>cliente@labcloud.com — cliente</li>
          </ul>
        </div>
      </div>
    </main>
  );
}
