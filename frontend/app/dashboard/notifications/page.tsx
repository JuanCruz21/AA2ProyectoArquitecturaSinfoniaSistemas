'use client';

import { useCallback, useEffect, useState } from 'react';

import { Card, EmptyState, ErrorAlert, Loading } from '@/components/ui';
import { getErrorMessage, notificationService } from '@/lib/api';
import type { Notification } from '@/lib/types';

/** Bandeja de notificaciones del usuario autenticado. */
export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await notificationService.getMine();
      setNotifications(data);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, 'No se pudieron cargar las notificaciones'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const markAsRead = async (id: number) => {
    try {
      await notificationService.markAsRead(id);
      // Se actualiza solo el elemento afectado, sin recargar toda la lista.
      setNotifications((previous) =>
        previous.map((item) => (item.id === id ? { ...item, is_read: true } : item)),
      );
    } catch (err) {
      setError(getErrorMessage(err, 'No se pudo marcar la notificación'));
    }
  };

  const unread = notifications.filter((item) => !item.is_read).length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Notificaciones</h1>
        <p className="text-sm text-gray-600">
          {unread === 0 ? 'Todo al día.' : `${unread} sin leer.`}
        </p>
      </div>

      <ErrorAlert message={error} />

      <Card>
        {loading ? (
          <Loading />
        ) : notifications.length === 0 ? (
          <EmptyState message="No tiene notificaciones." />
        ) : (
          <ul className="divide-y divide-gray-100">
            {notifications.map((notification) => (
              <li
                key={notification.id}
                className="flex items-start justify-between gap-4 py-3 first:pt-0 last:pb-0"
              >
                <div>
                  <p
                    className={
                      notification.is_read ? 'text-sm text-gray-500' : 'text-sm font-medium text-gray-900'
                    }
                  >
                    {notification.message}
                  </p>
                  <p className="mt-0.5 text-xs text-gray-400">
                    Solicitud #{notification.request_id} ·{' '}
                    {new Date(notification.created_at).toLocaleString('es')}
                  </p>
                </div>

                {!notification.is_read && (
                  <button
                    type="button"
                    className="btn-secondary btn-sm shrink-0"
                    onClick={() => markAsRead(notification.id)}
                  >
                    Marcar leída
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
