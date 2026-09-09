import Link from 'next/link';

/**
 * Pagina de bienvenida.
 *
 * Es un componente de servidor: no necesita estado ni interactividad, por lo
 * que no lleva la directiva `'use client'` y Next.js la envia como HTML puro.
 */
export default function HomePage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <header className="mb-12">
        <p className="mb-2 text-sm font-semibold uppercase tracking-wide text-brand-600">
          LabCloud
        </p>
        <h1 className="mb-4 text-4xl font-bold text-gray-900">
          Gestión de análisis de laboratorio
        </h1>
        <p className="max-w-2xl text-lg text-gray-600">
          Registre clientes y muestras, haga seguimiento de las solicitudes de análisis y
          entregue los resultados desde un único lugar.
        </p>
        <div className="mt-8 flex gap-3">
          <Link href="/auth/login" className="btn-primary">
            Iniciar sesión
          </Link>
          <Link href="/auth/register" className="btn-secondary">
            Crear cuenta
          </Link>
        </div>
      </header>

      <section className="grid gap-6 md:grid-cols-2">
        <article className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-3 font-semibold text-gray-800">Qué puede hacer cada rol</h2>
          <dl className="space-y-2 text-sm text-gray-600">
            <div>
              <dt className="inline font-medium text-gray-800">Recepción: </dt>
              <dd className="inline">registra clientes, muestras y solicitudes.</dd>
            </div>
            <div>
              <dt className="inline font-medium text-gray-800">Analista: </dt>
              <dd className="inline">procesa las solicitudes asignadas y emite resultados.</dd>
            </div>
            <div>
              <dt className="inline font-medium text-gray-800">Cliente: </dt>
              <dd className="inline">consulta el estado de sus análisis y sus resultados.</dd>
            </div>
            <div>
              <dt className="inline font-medium text-gray-800">Administrador: </dt>
              <dd className="inline">gestiona usuarios y supervisa toda la operación.</dd>
            </div>
          </dl>
        </article>

        <article className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-3 font-semibold text-gray-800">Arquitectura</h2>
          <p className="mb-3 text-sm text-gray-600">
            Backend en Python con FastAPI y SQLite, organizado en cuatro capas (presentación,
            aplicación, dominio e infraestructura) sobre seis servicios. Frontend en Next.js
            con React y TypeScript.
          </p>
          <p className="text-sm text-gray-500">
            Con el backend en marcha, la documentación interactiva de la API está en{' '}
            <code className="rounded bg-gray-100 px-1 py-0.5">/docs</code>.
          </p>
        </article>
      </section>
    </main>
  );
}
