'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import { Card, EmptyState, ErrorAlert, Field, Loading, StatusBadge, SuccessAlert, Table } from '@/components/ui';
import {
  clientService,
  getErrorMessage,
  requestService,
  resultService,
  sampleService,
  userService,
} from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { AnalysisRequest, Client, Result, Sample, User } from '@/lib/types';

const EMPTY_REQUEST_FORM = { client_id: '', sample_id: '', test_type: '' };

/**
 * Pantalla principal de solicitudes.
 *
 * Muestra acciones distintas segun el rol: recepcion crea y asigna, el analista
 * procesa y emite resultados, y el cliente solo consulta. El backend vuelve a
 * comprobar cada permiso, de modo que ocultar un boton es una comodidad visual
 * y no la medida de seguridad.
 */
export default function RequestsPage() {
  const { session, hasRole } = useAuth();
  const isStaff = hasRole('admin', 'receptionist');
  const isAnalyst = hasRole('analyst');

  const [requests, setRequests] = useState<AnalysisRequest[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [analysts, setAnalysts] = useState<User[]>([]);
  const [results, setResults] = useState<Result[]>([]);

  const [requestForm, setRequestForm] = useState(EMPTY_REQUEST_FORM);
  const [resultDraft, setResultDraft] = useState<{ requestId: number | null; value: string; notes: string }>({
    requestId: null,
    value: '',
    notes: '',
  });

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [requestsResponse, resultsResponse] = await Promise.all([
        requestService.getAll(),
        resultService.getAll(),
      ]);
      setRequests(requestsResponse.data);
      setResults(resultsResponse.data);

      // Los catalogos del formulario de alta solo los necesita el personal
      // que puede crear o asignar solicitudes.
      if (isStaff) {
        const [clientsResponse, samplesResponse, analystsResponse] = await Promise.all([
          clientService.getAll(),
          sampleService.getAll(),
          userService.getAnalysts(),
        ]);
        setClients(clientsResponse.data);
        setSamples(samplesResponse.data);
        setAnalysts(analystsResponse.data);
      }
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, 'No se pudieron cargar las solicitudes'));
    } finally {
      setLoading(false);
    }
  }, [isStaff]);

  useEffect(() => {
    void load();
  }, [load]);

  /** Muestras del cliente elegido: evita crear una solicitud cruzada. */
  const availableSamples = useMemo(
    () => samples.filter((sample) => String(sample.client_id) === requestForm.client_id),
    [samples, requestForm.client_id],
  );

  /** Envuelve una accion para unificar el manejo de errores y el estado de carga. */
  const run = async (action: () => Promise<void>, successMessage: string) => {
    setError(null);
    setSuccess(null);
    setBusy(true);
    try {
      await action();
      setSuccess(successMessage);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'No se pudo completar la operación'));
    } finally {
      setBusy(false);
    }
  };

  const handleCreate = (event: React.FormEvent) => {
    event.preventDefault();
    void run(async () => {
      await requestService.create({
        client_id: Number(requestForm.client_id),
        sample_id: Number(requestForm.sample_id),
        test_type: requestForm.test_type,
      });
      setRequestForm(EMPTY_REQUEST_FORM);
    }, 'Solicitud creada. Se ha notificado al cliente.');
  };

  const handleAssign = (requestId: number, analystId: string) => {
    if (!analystId) return;
    void run(
      () => requestService.assignAnalyst(requestId, Number(analystId)).then(() => undefined),
      'Analista asignado.',
    );
  };

  const handleStart = (requestId: number) =>
    void run(
      () => requestService.changeStatus(requestId, 'in_analysis').then(() => undefined),
      'La solicitud pasó a "en análisis".',
    );

  const handleCancel = (requestId: number) =>
    void run(
      () => requestService.changeStatus(requestId, 'cancelled').then(() => undefined),
      'Solicitud cancelada.',
    );

  const handleSubmitResult = (event: React.FormEvent) => {
    event.preventDefault();
    if (!resultDraft.requestId) return;
    void run(async () => {
      await resultService.create({
        request_id: resultDraft.requestId as number,
        result_value: resultDraft.value,
        result_notes: resultDraft.notes,
      });
      setResultDraft({ requestId: null, value: '', notes: '' });
    }, 'Resultado registrado. La solicitud queda completada.');
  };

  const resultOf = (requestId: number) => results.find((item) => item.request_id === requestId);
  const clientName = (clientId: number) =>
    clients.find((client) => client.id === clientId)?.name ?? `Cliente ${clientId}`;

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Solicitudes de análisis</h1>

      <ErrorAlert message={error} />
      <SuccessAlert message={success} />

      {isStaff && (
        <Card title="Nueva solicitud">
          <form onSubmit={handleCreate} className="grid gap-4 sm:grid-cols-3">
            <Field label="Cliente" htmlFor="req-client">
              <select
                id="req-client"
                className="form-input"
                value={requestForm.client_id}
                onChange={(event) =>
                  // Al cambiar de cliente se limpia la muestra: la anterior
                  // pertenecia a otro cliente y el backend la rechazaria.
                  setRequestForm({ ...requestForm, client_id: event.target.value, sample_id: '' })
                }
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

            <Field
              label="Muestra"
              htmlFor="req-sample"
              hint={
                requestForm.client_id && availableSamples.length === 0
                  ? 'Este cliente no tiene muestras registradas.'
                  : undefined
              }
            >
              <select
                id="req-sample"
                className="form-input"
                value={requestForm.sample_id}
                onChange={(event) =>
                  setRequestForm({ ...requestForm, sample_id: event.target.value })
                }
                disabled={!requestForm.client_id}
                required
              >
                <option value="">Seleccione…</option>
                {availableSamples.map((sample) => (
                  <option key={sample.id} value={sample.id}>
                    {sample.sample_code} · {sample.sample_type}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Tipo de análisis" htmlFor="req-test">
              <input
                id="req-test"
                className="form-input"
                value={requestForm.test_type}
                onChange={(event) =>
                  setRequestForm({ ...requestForm, test_type: event.target.value })
                }
                placeholder="Hemograma completo"
                minLength={2}
                required
              />
            </Field>

            <div className="sm:col-span-3">
              <button type="submit" className="btn-primary" disabled={busy}>
                {busy ? 'Guardando…' : 'Crear solicitud'}
              </button>
            </div>
          </form>
        </Card>
      )}

      <Card title={`Solicitudes (${requests.length})`}>
        {requests.length === 0 ? (
          <EmptyState message="No hay solicitudes que mostrar." />
        ) : (
          <Table
            columns={
              isStaff
                ? ['Código', 'Cliente', 'Análisis', 'Estado', 'Analista', 'Acciones']
                : ['Código', 'Análisis', 'Estado', 'Resultado', 'Acciones']
            }
          >
            {requests.map((request) => {
              const result = resultOf(request.id);
              const mine = request.assigned_analyst_id === session?.user_id;

              return (
                <tr key={request.id}>
                  <td className="px-3 py-2 font-mono text-xs">{request.request_code}</td>

                  {isStaff && <td className="px-3 py-2">{clientName(request.client_id)}</td>}

                  <td className="px-3 py-2">{request.test_type}</td>

                  <td className="px-3 py-2">
                    <StatusBadge status={request.status} />
                  </td>

                  {isStaff ? (
                    <td className="px-3 py-2">
                      {request.status === 'pending' || request.status === 'in_analysis' ? (
                        <select
                          className="form-input py-1 text-xs"
                          value={request.assigned_analyst_id ?? ''}
                          onChange={(event) => handleAssign(request.id, event.target.value)}
                          disabled={busy}
                          aria-label={`Asignar analista a ${request.request_code}`}
                        >
                          <option value="">Sin asignar</option>
                          {analysts.map((analyst) => (
                            <option key={analyst.id} value={analyst.id}>
                              {analyst.full_name}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="text-gray-500">
                          {analysts.find((a) => a.id === request.assigned_analyst_id)?.full_name ??
                            '—'}
                        </span>
                      )}
                    </td>
                  ) : (
                    <td className="px-3 py-2 text-gray-600">
                      {result ? result.result_value : '—'}
                    </td>
                  )}

                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-2">
                      {isAnalyst && mine && request.status === 'pending' && (
                        <button
                          type="button"
                          className="btn-secondary btn-sm"
                          onClick={() => handleStart(request.id)}
                          disabled={busy}
                        >
                          Iniciar análisis
                        </button>
                      )}

                      {isAnalyst && mine && request.status === 'in_analysis' && (
                        <button
                          type="button"
                          className="btn-primary btn-sm"
                          onClick={() =>
                            setResultDraft({ requestId: request.id, value: '', notes: '' })
                          }
                          disabled={busy}
                        >
                          Registrar resultado
                        </button>
                      )}

                      {isStaff && (request.status === 'pending' || request.status === 'in_analysis') && (
                        <button
                          type="button"
                          className="btn-secondary btn-sm"
                          onClick={() => handleCancel(request.id)}
                          disabled={busy}
                        >
                          Cancelar
                        </button>
                      )}

                      {request.status === 'completed' && !isStaff && result && (
                        <span className="text-xs text-gray-500">{result.result_notes || '—'}</span>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </Table>
        )}
      </Card>

      {resultDraft.requestId !== null && (
        <Card title="Registrar resultado">
          <form onSubmit={handleSubmitResult} className="space-y-4">
            <Field label="Valor del resultado" htmlFor="result-value">
              <input
                id="result-value"
                className="form-input"
                value={resultDraft.value}
                onChange={(event) =>
                  setResultDraft({ ...resultDraft, value: event.target.value })
                }
                placeholder="Hemoglobina 14.2 g/dL"
                required
              />
            </Field>

            <Field label="Observaciones" htmlFor="result-notes">
              <textarea
                id="result-notes"
                className="form-input"
                rows={3}
                value={resultDraft.notes}
                onChange={(event) =>
                  setResultDraft({ ...resultDraft, notes: event.target.value })
                }
                placeholder="Valores dentro del rango de referencia."
              />
            </Field>

            <div className="flex gap-2">
              <button type="submit" className="btn-primary" disabled={busy}>
                {busy ? 'Guardando…' : 'Guardar resultado'}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setResultDraft({ requestId: null, value: '', notes: '' })}
              >
                Cancelar
              </button>
            </div>
          </form>
        </Card>
      )}
    </div>
  );
}
