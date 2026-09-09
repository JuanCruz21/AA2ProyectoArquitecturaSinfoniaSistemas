# LabCloud · Frontend

Interfaz web del sistema de gestión de análisis de laboratorio. Next.js 14 con React 18, TypeScript y Tailwind CSS.

Para la visión de conjunto del proyecto consulte el `README.md` de la raíz; para el diseño en detalle, `ARQUITECTURA.md`.

---

## Arrancar

```bash
npm install
npm run dev
```

La aplicación queda en http://localhost:3000.

**El backend debe estar en marcha** en http://localhost:8000; si no, el inicio de sesión avisa de que no puede conectar. El archivo `.env` ya viene incluido apuntando a esa dirección, así que no hace falta configurar nada.

---

## Comandos

| Qué hace | Comando |
|---|---|
| Instalar dependencias | `npm install` |
| Arrancar en desarrollo | `npm run dev` |
| Compilar para producción | `npm run build` |
| Servir la compilación | `npm start` |
| Comprobar tipos | `npm run typecheck` |
| Revisar el código | `npm run lint` |

---

## Estructura

```
frontend/
├── .env                    Configuración local (lista para usar)
├── .env.example            Plantilla de configuración
│
├── app/                    Rutas (App Router de Next.js)
│   ├── layout.tsx          Layout raíz · monta el contexto de sesión
│   ├── page.tsx            Página de bienvenida
│   ├── icon.svg            Icono de la aplicación
│   ├── globals.css         Estilos base y clases propias
│   │
│   ├── auth/
│   │   ├── login/          Inicio de sesión
│   │   └── register/       Registro de clientes
│   │
│   └── dashboard/
│       ├── layout.tsx      Guarda de ruta y navegación por rol
│       ├── page.tsx        Resumen
│       ├── requests/       Solicitudes: crear, asignar, procesar, resultados
│       ├── clients/        Clientes
│       ├── samples/        Muestras
│       ├── users/          Usuarios (solo administrador)
│       └── notifications/  Bandeja de avisos
│
├── components/
│   └── ui.tsx              Card, Table, StatusBadge, Field, alertas…
│
└── lib/
    ├── api.ts              Cliente HTTP, servicios por recurso, manejo de errores
    ├── auth.tsx            Contexto de sesión y hook `useAuth()`
    └── types.ts            Tipos que reflejan los esquemas del backend
```

---

## Cómo está organizado

**Toda llamada a la API pasa por `lib/api.ts`.** Ninguna pantalla construye una URL por su cuenta. Ese módulo adjunta el token en cada petición, cierra la sesión automáticamente ante un 401 y traduce los errores de axios a mensajes legibles con `getErrorMessage()`.

**La sesión vive en `lib/auth.tsx`.** El hook `useAuth()` da acceso a la sesión activa y a `hasRole(...)`, que es lo que decide qué ve cada usuario. La sesión se lee de `localStorage` dentro de un `useEffect`, porque Next.js también renderiza las páginas en el servidor, donde `localStorage` no existe.

**Los tipos de `lib/types.ts` reflejan los esquemas del backend.** Si una pantalla usa un campo que la API no devuelve, TypeScript avisa al compilar en lugar de fallar en el navegador.

**La navegación se filtra por rol** en `app/dashboard/layout.tsx`, que además redirige al login si no hay sesión. Es una comodidad visual, no una medida de seguridad: quien decide de verdad es el backend, que valida token y rol en cada petición.

---

## Configuración

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Dirección de la API del backend |

El prefijo `NEXT_PUBLIC_` es obligatorio para que la variable llegue al navegador. Se incrusta al compilar, así que tras cambiarla hay que reiniciar `npm run dev`.

Si cambia el puerto del backend, añada el nuevo origen del frontend a `CORS_ORIGINS` en `backend/.env`. Para el navegador, `localhost` y `127.0.0.1` son orígenes distintos.
