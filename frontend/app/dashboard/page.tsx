'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

import { Card, EmptyState, ErrorAlert, Loading, StatusBadge, Table } from '@/components/ui';
import { getErrorMessage, notificationService, requestService } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { AnalysisRequest, Notification, RequestStatus } from '@/lib/types';
import { STATUS_LABELS } from '@/lib/types';

/** Estados que se resumen en las tarjetas superiores. */
const SUMMARY_STATUSES: RequestStatus[] = ['pending', 'in_analysis', 'completed', 'cancelled'];

/** Pagina de resumen del panel, adaptada al rol de quien la consulta. */
export default function DashboardPage() {
  const { session } = useAuth();
  const [requests, setRequests] = useState<AnalysisRequest[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Las dos peticiones son independientes, asi que se lanzan en paralelo.
      const [requestsResponse, notificationsResponse] = await Promise.all([
        requestService.getAll(),
        notificationService.getMine(),
      ]);
      setRequests(requestsResponse.data);
      setNotifications(notificationsResponse.data);
    } catch (err) {
      setError(getErrorMessage(err, 'No se pudieron cargar los datos'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) return <Loading />;

  const unread = notifications.filter((item) => !item.is_read).length;
  const recent = requests.slice(0, 5);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Hola, {session?.full_name.split(' ')[0]}
        </h1>
        <p className="text-sm text-gray-600">
          {unread > 0
            ? `Tiene ${unread} ${unread === 1 ? 'notificación sin leer' : 'notificaciones sin leer'}.`
            : 'No tiene notificaciones pendientes.'}
        </p>
      </div>

      <ErrorAlert message={error} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {SUMMARY_STATUSES.map((status) => (
          <div
            key={status}
            className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
          >
            <p className="text-xs uppercase tracking-wide text-gray-500">
              {STATUS_LABELS[status]}
            </p>
            <p className="mt-1 text-2xl font-semibold text-gray-900">
              {requests.filter((request) => request.status === status).length}
            </p>
          </div>
        ))}
      </div>

      <Card
        title="Últimas solicitudes"
        action={
          <Link href="/dashboard/requests" className="text-sm text-brand-600 hover:underline">
            Ver todas
          </Link>
        }
      >
        {recent.length === 0 ? (
          <EmptyState message="Todavía no hay solicitudes registradas." />
        ) : (
          <Table columns={['Código', 'Análisis', 'Estado', 'Actualizada']}>
            {recent.map((request) => (
              <tr key={request.id}>
                <td className="px-3 py-2 font-mono text-xs">{request.request_code}</td>
                <td className="px-3 py-2">{request.test_type}</td>
                <td className="px-3 py-2">
                  <StatusBadge status={request.status} />
                </td>
                <td className="px-3 py-2 text-gray-500">
                  {new Date(request.updated_at).toLocaleDateString('es')}
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </div>
  );
}
