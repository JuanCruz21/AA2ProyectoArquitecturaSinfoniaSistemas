'use client';

import { useCallback, useEffect, useState } from 'react';

import { Card, EmptyState, ErrorAlert, Field, Loading, SuccessAlert, Table } from '@/components/ui';
import { clientService, getErrorMessage, sampleService } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { Client, Sample } from '@/lib/types';

/** Registro y consulta de muestras. */
export default function SamplesPage() {
  const { hasRole } = useAuth();
  const canRegister = hasRole('admin', 'receptionist');

  const [samples, setSamples] = useState<Sample[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [form, setForm] = useState({ sample_type: '', description: '', client_id: '' });
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const samplesResponse = await sampleService.getAll();
      setSamples(samplesResponse.data);

      // Solo quien puede registrar muestras necesita la lista de clientes para
      // el desplegable; para un analista ese endpoint no aporta nada.
      if (canRegister) {
        const clientsResponse = await clientService.getAll();
        setClients(clientsResponse.data);
      }
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, 'No se pudieron cargar las muestras'));
    } finally {
      setLoading(false);
    }
  }, [canRegister]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
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
      const { data } = await sampleService.create({
        sample_type: form.sample_type,
        description: form.description,
        client_id: Number(form.client_id),
      });
      setForm({ sample_type: '', description: '', client_id: '' });
      setSuccess(`Muestra ${data.sample_code} registrada.`);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'No se pudo registrar la muestra'));
    } finally {
      setSaving(false);
    }
  };

  const clientName = (clientId: number) =>
    clients.find((client) => client.id === clientId)?.name ?? `Cliente ${clientId}`;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Muestras</h1>

      <ErrorAlert message={error} />
      <SuccessAlert message={success} />

      {canRegister && (
        <Card title="Registrar muestra">
          <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-3">
            <Field label="Cliente" htmlFor="client_id">
              <select
                id="client_id"
                name="client_id"
                className="form-input"
                value={form.client_id}
                onChange={handleChange}
                required
              >
                <option value="">Seleccione…</option>
                {clients.map((client) => (
                  <option key={client.id} value={client.id}>
                    {client.name}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Tipo de muestra" htmlFor="sample_type">
              <input
                id="sample_type"
                name="sample_type"
                className="form-input"
                value={form.sample_type}
                onChange={handleChange}
                placeholder="Sangre, orina…"
                minLength={2}
                required
              />
            </Field>

            <Field label="Descripción" htmlFor="description">
              <input
                id="description"
                name="description"
                className="form-input"
                value={form.description}
                onChange={handleChange}
                placeholder="Hemograma completo"
              />
            </Field>

            <div className="sm:col-span-3">
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? 'Guardando…' : 'Registrar muestra'}
              </button>
              <p className="mt-2 text-xs text-gray-500">
                El código de la muestra lo genera el sistema automáticamente.
              </p>
            </div>
          </form>
        </Card>
      )}

      <Card title={`Muestras registradas (${samples.length})`}>
        {loading ? (
          <Loading />
        ) : samples.length === 0 ? (
          <EmptyState message="Aún no hay muestras registradas." />
        ) : (
          <Table columns={['Código', 'Tipo', 'Descripción', 'Cliente', 'Recepción']}>
            {samples.map((sample) => (
              <tr key={sample.id}>
                <td className="px-3 py-2 font-mono text-xs">{sample.sample_code}</td>
                <td className="px-3 py-2">{sample.sample_type}</td>
                <td className="px-3 py-2 text-gray-600">{sample.description || '—'}</td>
                <td className="px-3 py-2">
                  {canRegister ? clientName(sample.client_id) : sample.client_id}
                </td>
                <td className="px-3 py-2 text-gray-500">
                  {new Date(sample.received_date).toLocaleDateString('es')}
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </div>
  );
}
