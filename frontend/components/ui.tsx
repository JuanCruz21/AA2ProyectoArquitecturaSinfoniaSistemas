'use client';

/**
 * Componentes de interfaz reutilizables.
 *
 * Agrupar aqui las piezas visuales comunes evita repetir las mismas clases de
 * Tailwind en cada pantalla y mantiene un aspecto uniforme.
 */

import type { RequestStatus } from '@/lib/types';
import { STATUS_LABELS, STATUS_STYLES } from '@/lib/types';

/** Tarjeta con titulo opcional. Es el contenedor base de las secciones. */
export function Card({
  title,
  action,
  children,
}: {
  title?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-gray-200 bg-white shadow-sm">
      {(title || action) && (
        <header className="flex items-center justify-between border-b border-gray-100 px-5 py-3">
          {title && <h2 className="font-semibold text-gray-800">{title}</h2>}
          {action}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

/** Etiqueta de color con el estado de una solicitud. */
export function StatusBadge({ status }: { status: RequestStatus }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}

/** Mensaje de error en rojo. No se muestra nada si `message` esta vacio. */
export function ErrorAlert({ message }: { message?: string | null }) {
  if (!message) return null;
  return (
    <p
      role="alert"
      className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
    >
      {message}
    </p>
  );
}

/** Mensaje de confirmacion en verde. */
export function SuccessAlert({ message }: { message?: string | null }) {
  if (!message) return null;
  return (
    <p className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
      {message}
    </p>
  );
}

/** Texto que se muestra cuando una tabla o lista no tiene datos. */
export function EmptyState({ message }: { message: string }) {
  return <p className="py-6 text-center text-sm text-gray-500">{message}</p>;
}

/** Indicador de carga. */
export function Loading({ message = 'Cargando…' }: { message?: string }) {
  return <p className="py-6 text-center text-sm text-gray-500">{message}</p>;
}

/** Campo de formulario con etiqueta asociada, accesible mediante `htmlFor`. */
export function Field({
  label,
  htmlFor,
  children,
  hint,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className="mb-1 block text-sm font-medium text-gray-700">
        {label}
      </label>
      {children}
      {hint && <p className="mt-1 text-xs text-gray-500">{hint}</p>}
    </div>
  );
}

/** Tabla con cabecera. `columns` son los titulos y `children` las filas. */
export function Table({
  columns,
  children,
}: {
  columns: string[];
  children: React.ReactNode;
}) {
  return (
    // El contenedor con scroll horizontal evita que la tabla desborde la
    // pagina en pantallas estrechas.
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-xs uppercase tracking-wide text-gray-500">
            {columns.map((column) => (
              <th key={column} className="px-3 py-2 font-medium">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">{children}</tbody>
      </table>
    </div>
  );
}
