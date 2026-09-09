'use client';

import { useCallback, useEffect, useState } from 'react';

import { Card, EmptyState, ErrorAlert, Field, Loading, SuccessAlert, Table } from '@/components/ui';
import { clientService, getErrorMessage } from '@/lib/api';
import type { Client } from '@/lib/types';

const EMPTY_FORM = { name: '', email: '', phone: '', address: '', user_id: '' };

/** Gestion de clientes del laboratorio (recepcion y administracion). */
export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await clientService.getAll();
      setClients(data);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, 'No se pudieron cargar los clientes'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setSaving(true);
    try {
      await clientService.create({
        name: form.name,
        email: form.email,
        phone: form.phone,
        address: form.address,
        // El campo es opcional: solo se envia si se indico una cuenta.
        user_id: form.user_id ? Number(form.user_id) : null,
      });
      setForm(EMPTY_FORM);
      setSuccess('Cliente registrado correctamente.');
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'No se pudo registrar el cliente'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Clientes</h1>

      <ErrorAlert message={error} />
      <SuccessAlert message={success} />

      <Card title="Registrar cliente">
        <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
          <Field label="Nombre" htmlFor="name">
            <input
              id="name"
              name="name"
              className="form-input"
              value={form.name}
              onChange={handleChange}
              placeholder="Clínica San José"
              minLength={2}
              required
            />
          </Field>

          <Field label="Correo electrónico" htmlFor="client-email">
            <input
              id="client-email"
              name="email"
              type="email"
              className="form-input"
              value={form.email}
              onChange={handleChange}
              placeholder="contacto@clinica.com"
              required
            />
          </Field>

          <Field label="Teléfono" htmlFor="phone">
            <input
              id="phone"
              name="phone"
              className="form-input"
              value={form.phone}
              onChange={handleChange}
              placeholder="+57 601 1234567"
            />
          </Field>

          <Field
            label="Cuenta de usuario asociada"
            htmlFor="user_id"
            hint="Opcional. Identificador del usuario que consultará estos resultados."
          >
            <input
              id="user_id"
              name="user_id"
              type="number"
              min={1}
              className="form-input"
              value={form.user_id}
              onChange={handleChange}
              placeholder="Ej.: 4"
            />
          </Field>

          <div className="sm:col-span-2">
            <Field label="Dirección" htmlFor="address">
              <input
                id="address"
                name="address"
                className="form-input"
                value={form.address}
                onChange={handleChange}
                placeholder="Calle 10 #5-50, Bogotá"
              />
            </Field>
          </div>

          <div className="sm:col-span-2">
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Guardando…' : 'Registrar cliente'}
            </button>
          </div>
        </form>
      </Card>

      <Card title={`Clientes registrados (${clients.length})`}>
        {loading ? (
          <Loading />
        ) : clients.length === 0 ? (
          <EmptyState message="Aún no hay clientes registrados." />
        ) : (
          <Table columns={['ID', 'Nombre', 'Correo', 'Teléfono', 'Cuenta']}>
            {clients.map((client) => (
              <tr key={client.id}>
                <td className="px-3 py-2 text-gray-500">{client.id}</td>
                <td className="px-3 py-2 font-medium">{client.name}</td>
                <td className="px-3 py-2">{client.email}</td>
                <td className="px-3 py-2">{client.phone || '—'}</td>
                <td className="px-3 py-2 text-gray-500">{client.user_id ?? 'Sin asociar'}</td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </div>
  );
}
