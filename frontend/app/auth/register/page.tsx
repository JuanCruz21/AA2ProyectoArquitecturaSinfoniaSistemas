'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { ErrorAlert, Field } from '@/components/ui';
import { authService, getErrorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';

/** Longitud minima exigida por el backend. */
const MIN_PASSWORD_LENGTH = 8;

/**
 * Pantalla de registro.
 *
 * No permite elegir rol: el registro publico siempre crea una cuenta de cliente.
 * Las cuentas de recepcion, analista o administrador las crea un administrador
 * desde el panel, para que nadie pueda auto-asignarse privilegios.
 */
export default function RegisterPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    // Validaciones en el cliente para dar respuesta inmediata. El backend
    // vuelve a comprobarlas: nunca se confia solo en la validacion del navegador.
    if (form.password !== form.confirmPassword) {
      setError('Las contraseñas no coinciden');
      return;
    }
    if (form.password.length < MIN_PASSWORD_LENGTH) {
      setError(`La contraseña debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres`);
      return;
    }

    setLoading(true);
    try {
      await authService.register(form.email, form.password, form.full_name);
      // Se inicia sesion automaticamente para no pedir las credenciales dos veces.
      await login(form.email, form.password);
      router.push('/dashboard');
    } catch (err) {
      setError(getErrorMessage(err, 'No se pudo completar el registro'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-md rounded-lg border border-gray-200 bg-white p-8 shadow-sm">
        <h1 className="mb-1 text-2xl font-bold text-gray-900">Crear cuenta</h1>
        <p className="mb-6 text-sm text-gray-600">
          Se creará una cuenta de cliente para consultar sus análisis.
        </p>

        <ErrorAlert message={error} />

        <form onSubmit={handleSubmit} className="space-y-4">
          <Field label="Nombre completo" htmlFor="full_name">
            <input
              id="full_name"
              name="full_name"
              type="text"
              className="form-input"
              value={form.full_name}
              onChange={handleChange}
              placeholder="Juan Pérez"
              minLength={3}
              required
            />
          </Field>

          <Field label="Correo electrónico" htmlFor="email">
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              className="form-input"
              value={form.email}
              onChange={handleChange}
              placeholder="usuario@ejemplo.com"
              required
            />
          </Field>

          <Field
            label="Contraseña"
            htmlFor="password"
            hint={`Mínimo ${MIN_PASSWORD_LENGTH} caracteres.`}
          >
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="new-password"
              className="form-input"
              value={form.password}
              onChange={handleChange}
              placeholder="••••••••"
              minLength={MIN_PASSWORD_LENGTH}
              required
            />
          </Field>

          <Field label="Repetir contraseña" htmlFor="confirmPassword">
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              autoComplete="new-password"
              className="form-input"
              value={form.confirmPassword}
              onChange={handleChange}
              placeholder="••••••••"
              required
            />
          </Field>

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? 'Creando cuenta…' : 'Crear cuenta'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-600">
          ¿Ya tiene cuenta?{' '}
          <Link href="/auth/login" className="font-medium text-brand-600 hover:underline">
            Inicie sesión
          </Link>
        </p>
      </div>
    </main>
  );
}
