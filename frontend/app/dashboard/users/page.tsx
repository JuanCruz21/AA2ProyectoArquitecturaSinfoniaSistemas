'use client';

import { useCallback, useEffect, useState } from 'react';

import { Card, EmptyState, ErrorAlert, Field, Loading, SuccessAlert, Table } from '@/components/ui';
import { getErrorMessage, userService } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { User, UserRole } from '@/lib/types';
import { ROLE_LABELS } from '@/lib/types';

const ROLES: UserRole[] = ['admin', 'receptionist', 'analyst', 'client'];
const EMPTY_FORM = { full_name: '', email: '', password: '', role: 'analyst' as UserRole };

/** Administracion de usuarios. Solo accesible para el rol `admin`. */
export default function UsersPage() {
  const { session } = useAuth();

  const [users, setUsers] = useState<User[]>([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await userService.getAll();
      setUsers(data);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, 'No se pudieron cargar los usuarios'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setBusy(true);
    try {
      await userService.create(form);
      setForm(EMPTY_FORM);
      setSuccess('Usuario creado.');
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'No se pudo crear el usuario'));
    } finally {
      setBusy(false);
    }
  };

  const handleRoleChange = async (userId: number, role: UserRole) => {
    setError(null);
    try {
      await userService.setRole(userId, role);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'No se pudo cambiar el rol'));
    }
  };

  const handleToggleActive = async (user: User) => {
    setError(null);
    try {
      await userService.setActive(user.id, !user.is_active);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'No se pudo cambiar el estado de la cuenta'));
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Usuarios</h1>

      <ErrorAlert message={error} />
      <SuccessAlert message={success} />

      <Card title="Crear usuario">
        <form onSubmit={handleCreate} className="grid gap-4 sm:grid-cols-4">
          <Field label="Nombre completo" htmlFor="u-name">
            <input
              id="u-name"
              className="form-input"
              value={form.full_name}
              onChange={(event) => setForm({ ...form, full_name: event.target.value })}
              minLength={3}
              required
            />
          </Field>

          <Field label="Correo" htmlFor="u-email">
            <input
              id="u-email"
              type="email"
              className="form-input"
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
              required
            />
          </Field>

          <Field label="Contraseña" htmlFor="u-password" hint="Mínimo 8 caracteres.">
            <input
              id="u-password"
              type="password"
              className="form-input"
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
              minLength={8}
              required
            />
          </Field>

          <Field label="Rol" htmlFor="u-role">
            <select
              id="u-role"
              className="form-input"
              value={form.role}
              onChange={(event) => setForm({ ...form, role: event.target.value as UserRole })}
            >
              {ROLES.map((role) => (
                <option key={role} value={role}>
                  {ROLE_LABELS[role]}
                </option>
              ))}
            </select>
          </Field>

          <div className="sm:col-span-4">
            <button type="submit" className="btn-primary" disabled={busy}>
              {busy ? 'Creando…' : 'Crear usuario'}
            </button>
          </div>
        </form>
      </Card>

      <Card title={`Usuarios registrados (${users.length})`}>
        {loading ? (
          <Loading />
        ) : users.length === 0 ? (
          <EmptyState message="No hay usuarios." />
        ) : (
          <Table columns={['ID', 'Nombre', 'Correo', 'Rol', 'Estado', '']}>
            {users.map((user) => {
              const isSelf = user.id === session?.user_id;
              return (
                <tr key={user.id}>
                  <td className="px-3 py-2 text-gray-500">{user.id}</td>
                  <td className="px-3 py-2 font-medium">
                    {user.full_name}
                    {isSelf && <span className="ml-2 text-xs text-gray-400">(usted)</span>}
                  </td>
                  <td className="px-3 py-2">{user.email}</td>
                  <td className="px-3 py-2">
                    <select
                      className="form-input py-1 text-xs"
                      value={user.role}
                      onChange={(event) =>
                        handleRoleChange(user.id, event.target.value as UserRole)
                      }
                      aria-label={`Rol de ${user.full_name}`}
                    >
                      {ROLES.map((role) => (
                        <option key={role} value={role}>
                          {ROLE_LABELS[role]}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        user.is_active
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-gray-200 text-gray-600'
                      }`}
                    >
                      {user.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    {/* El backend impide desactivarse a uno mismo; aquí se
                        oculta el botón para no ofrecer una acción que fallaría. */}
                    {!isSelf && (
                      <button
                        type="button"
                        className="btn-secondary btn-sm"
                        onClick={() => handleToggleActive(user)}
                      >
                        {user.is_active ? 'Desactivar' : 'Activar'}
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </Table>
        )}
      </Card>
    </div>
  );
}
