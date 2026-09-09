# LabCloud

> **AA2 · Actividad 2. Orquestando códigos: la sinfonía de los sistemas**
> Asignatura de Arquitectura de Software · Tecnológica de Oriente

Sistema de gestión de análisis de laboratorio. Permite a recepción registrar clientes, muestras y solicitudes; a los analistas procesar los análisis asignados y emitir resultados; y a los clientes consultar el estado de sus solicitudes y sus resultados.

Proyecto académico de la asignatura de Arquitectura de Software. Implementa una arquitectura por capas organizada en seis servicios, con API REST en Python y una interfaz web en Next.js.

| | |
|---|---|
| **Backend** | Python 3.10+ · FastAPI · SQLAlchemy · SQLite · JWT |
| **Frontend** | Next.js 14 · React 18 · TypeScript · Tailwind CSS |
| **Gestor de paquetes** | `uv` (backend) · `npm` (frontend) |
| **Pruebas** | pytest — 43 pruebas |

---

## Requisitos previos

Necesita tres cosas instaladas:

1. **Python 3.10 o superior** — compruébelo con `python3 --version`.
2. **uv**, el gestor de entornos y dependencias de Python:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh      # Linux y macOS
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows
   ```
3. **Node.js 18 o superior** con npm — compruébelo con `node --version`.

---

## Puesta en marcha

Hacen falta **dos terminales**, una para el backend y otra para el frontend.

### Terminal 1 — Backend

```bash
cd backend

# 1. Instala las dependencias y crea el entorno virtual (.venv)
uv sync --extra dev

# 2. Crea la base de datos y la llena con datos de prueba
uv run python init_db.py

# 3. Arranca la API
uv run uvicorn main:app --reload --reload-exclude '.venv/*'
```

No hace falta configurar nada: cada carpeta trae su `.env` ya listo para desarrollo.

La API queda en **http://localhost:8000**, con la documentación interactiva en **http://localhost:8000/docs**.

### Terminal 2 — Frontend

```bash
cd frontend

# 1. Instala las dependencias
npm install

# 2. Arranca el servidor de desarrollo
npm run dev
```

La aplicación queda en **http://localhost:3000**.

Abra esa dirección, inicie sesión con cualquiera de las cuentas de la tabla siguiente y ya está funcionando.

---

## Cuentas de prueba

Las crea `init_db.py`. Todas usan la contraseña **`password123`**.

| Rol | Correo | Qué puede hacer |
|---|---|---|
| Administrador | `admin@labcloud.com` | Gestionar usuarios y supervisar toda la operación |
| Recepcionista | `recepcion@labcloud.com` | Registrar clientes, muestras y solicitudes; asignar analistas |
| Analista | `analista@labcloud.com` | Procesar sus solicitudes y registrar resultados |
| Cliente | `cliente@labcloud.com` | Consultar sus solicitudes, resultados y notificaciones |

El script deja además una solicitud ya creada, asignada al analista y en estado *en análisis*, para poder probar el registro de resultados nada más entrar.

---

## Cómo se usa

El recorrido completo del laboratorio es este:

1. **Recepción** registra el cliente en *Clientes*. Si el cliente va a consultar sus resultados por su cuenta, se indica el identificador de su usuario en el campo «Cuenta de usuario asociada».
2. **Recepción** registra la muestra en *Muestras*. El código (`MUE-AAAAMMDD-XXXXXX`) lo genera el sistema.
3. **Recepción** crea la solicitud en *Solicitudes*, eligiendo cliente, muestra y tipo de análisis. La solicitud nace en estado *pendiente* y el cliente recibe una notificación automática.
4. **Recepción** asigna un analista desde el desplegable de la propia tabla.
5. **El analista** entra, ve la solicitud en su lista y pulsa «Iniciar análisis»: pasa a *en análisis*.
6. **El analista** pulsa «Registrar resultado», introduce el valor y las observaciones. La solicitud pasa automáticamente a *completada* y se notifica al cliente.
7. **El cliente** consulta el resultado y sus notificaciones desde su panel.

---

## Ejecutar las pruebas

```bash
cd backend
uv run pytest -v
```

Son 43 pruebas repartidas en dos archivos:

- `tests/test_domain.py` — reglas de negocio puras (máquina de estados de la solicitud, roles, hash de contraseñas y tokens). No necesitan base de datos ni servidor.
- `tests/test_api.py` — pruebas de integración que recorren la aplicación entera contra una base SQLite en memoria: autenticación, control de acceso por rol, flujo completo del laboratorio y aislamiento de los datos de cada cliente.

Comprobaciones del frontend:

```bash
cd frontend
npm run typecheck   # TypeScript
npm run lint        # ESLint
npm run build       # Compilación de producción
```

---

## Arquitectura

`ARQUITECTURA.md` desarrolla el diseño en detalle. En resumen:

### Cuatro capas

```
┌─────────────────────────────────────────────┐
│ PRESENTACIÓN   app/presentation/            │
│ Endpoints REST, validación (Pydantic), RBAC │
├─────────────────────────────────────────────┤
│ APLICACIÓN     app/application/             │
│ Casos de uso, orquestación, eventos         │
├─────────────────────────────────────────────┤
│ DOMINIO        app/domain/                  │
│ Entidades, reglas de negocio, interfaces    │
├─────────────────────────────────────────────┤
│ INFRAESTRUCTURA app/infrastructure/         │
│ SQLAlchemy, SQLite, repositorios            │
└─────────────────────────────────────────────┘
```

Las dependencias van siempre hacia dentro: el dominio no importa nada de FastAPI ni de SQLAlchemy, por lo que sus reglas se prueban de forma aislada y se podría cambiar SQLite por PostgreSQL sin tocarlo.

### Seis servicios

Usuarios y autenticación, Clientes, Muestras, Solicitudes, Resultados y Notificaciones. Cada uno tiene su servicio de aplicación, su repositorio y su router.

### Patrones aplicados

- **API Gateway** — FastAPI centraliza el acceso, CORS, autenticación y el enrutado a cada servicio.
- **Repository** — el dominio declara interfaces (`app/domain/repositories.py`) y la infraestructura las implementa con SQLAlchemy.
- **Unit of Work** — la dependencia `get_db()` confirma la transacción una sola vez al final de cada petición y la deshace entera si algo falla, de modo que una operación compuesta (registrar un resultado y cerrar la solicitud) no puede quedar a medias.
- **Event-Driven** — los servicios publican eventos (`REQUEST_CREATED`, `RESULT_REGISTERED`…) y las notificaciones se generan como reacción a ellos, sin que exista dependencia directa entre ambos módulos.
- **Inyección de dependencias** — todo se ensambla en `app/presentation/dependencies.py`.
- **Máquina de estados** — el ciclo de vida de la solicitud vive en la entidad `Request`.

### Ciclo de vida de una solicitud

```
PENDING ──► IN_ANALYSIS ──► COMPLETED
   │              │
   └──────────────┴────────► CANCELLED
```

`COMPLETED` y `CANCELLED` son estados finales. El paso a `COMPLETED` no se hace cambiando el estado a mano, sino registrando el resultado en `POST /api/results/`.

### Seguridad

- Contraseñas con hash **bcrypt** y sal aleatoria por usuario.
- Autenticación por **JWT** con caducidad de 30 minutos; el token se valida y el usuario se relee de la base de datos en cada petición, de forma que una cuenta desactivada pierde el acceso de inmediato.
- **Control de acceso por rol** mediante la dependencia reutilizable `require_roles(...)`.
- Cada cliente solo ve sus propios datos: los listados se filtran por la ficha de cliente asociada a su cuenta.
- El registro público siempre crea un usuario con rol `client`; los roles privilegiados los asigna un administrador.
- El identificador del analista que firma un resultado se toma del token, nunca del cuerpo de la petición.

---

## Endpoints principales

Todos, salvo `/health`, `/api/auth/register` y `/api/auth/login`, requieren la cabecera `Authorization: Bearer <token>`.

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/auth/register` | Registrar cuenta de cliente |
| `POST` | `/api/auth/login` | Iniciar sesión y obtener el token |
| `GET` | `/api/auth/me` | Perfil del usuario autenticado |
| `POST` | `/api/users/` | Crear usuario con rol (admin) |
| `GET` | `/api/users/analysts` | Listar analistas disponibles |
| `PUT` | `/api/users/{id}/role` | Cambiar el rol de un usuario (admin) |
| `POST` | `/api/clients/` | Registrar cliente |
| `GET` | `/api/clients/` | Listar clientes visibles |
| `POST` | `/api/samples/` | Registrar muestra |
| `GET` | `/api/samples/client/{id}` | Muestras de un cliente |
| `POST` | `/api/requests/` | Crear solicitud de análisis |
| `GET` | `/api/requests/mine` | Mis solicitudes |
| `GET` | `/api/requests/status/{estado}` | Solicitudes por estado |
| `PUT` | `/api/requests/{id}/analyst` | Asignar analista |
| `PUT` | `/api/requests/{id}/status` | Cambiar de estado |
| `POST` | `/api/results/` | Registrar resultado (analista) |
| `GET` | `/api/results/request/{id}` | Resultado de una solicitud |
| `GET` | `/api/notifications/mine` | Mis notificaciones |
| `PUT` | `/api/notifications/{id}/read` | Marcar como leída |

El listado completo, con esquemas de entrada y salida, está en http://localhost:8000/docs.

### Probar la API desde la terminal

```bash
# Iniciar sesión y guardar el token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"analista@labcloud.com","password":"password123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Consultar las solicitudes asignadas
curl -s http://localhost:8000/api/requests/mine -H "Authorization: Bearer $TOKEN"
```

En Swagger (`/docs`) basta con pulsar **Authorize** y pegar el token.

---

## Estructura del proyecto

El proyecto tiene dos partes independientes en la raíz. Cada una es autocontenida: trae su propio `README.md`, su `.gitignore` y su `.env` ya configurado.

```
labcloud_project/
├── README.md               Este archivo · visión de conjunto y puesta en marcha
├── ARQUITECTURA.md         Diseño, patrones y decisiones técnicas
├── .gitignore              Reglas comunes (editores y sistema operativo)
│
├── backend/                API REST · Python + FastAPI + SQLite
│   ├── README.md           Documentación del backend
│   ├── .gitignore          Entorno virtual, cache de Python, base de datos
│   ├── .env                Configuración local (lista para usar)
│   ├── .env.example        Plantilla de configuración
│   ├── pyproject.toml      Dependencias y configuración de pytest y ruff
│   ├── main.py             Punto de entrada · API Gateway
│   ├── init_db.py          Carga de datos de prueba
│   ├── app/
│   │   ├── core/           Configuración, seguridad, bus de eventos
│   │   ├── domain/         Entidades y reglas · interfaces de repositorio
│   │   ├── application/    Servicios de caso de uso · suscriptores
│   │   ├── infrastructure/ SQLAlchemy, SQLite, repositorios
│   │   └── presentation/   Esquemas, dependencias y routers REST
│   └── tests/              pytest (dominio + integración)
│
└── frontend/               Interfaz web · Next.js + React + TypeScript
    ├── README.md           Documentación del frontend
    ├── .gitignore          node_modules y compilación de Next.js
    ├── .env                Configuración local (lista para usar)
    ├── .env.example        Plantilla de configuración
    ├── package.json
    ├── app/
    │   ├── page.tsx        Página de bienvenida
    │   ├── auth/           Inicio de sesión y registro
    │   └── dashboard/      Panel: resumen, solicitudes, clientes,
    │                       muestras, usuarios y notificaciones
    ├── components/ui.tsx   Componentes reutilizables
    └── lib/                Cliente HTTP, tipos y contexto de sesión
```

Los `.env` se entregan rellenados con valores de desarrollo para que el proyecto arranque sin configuración previa. Aun así figuran en los `.gitignore`, que es la práctica correcta: en un repositorio real solo se versiona el `.env.example`.

---

## Configuración

### Backend — `backend/.env`

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `APP_NAME` | `LabCloud API` | Nombre que aparece en la documentación |
| `DEBUG` | `True` | Recarga automática y registro detallado |
| `DATABASE_URL` | `sqlite:///./labcloud.db` | Conexión a la base de datos |
| `SECRET_KEY` | *(clave de desarrollo)* | Clave de firma de los tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Vigencia del token |
| `MIN_PASSWORD_LENGTH` | `8` | Longitud mínima de contraseña |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Orígenes autorizados |

Si arranca la aplicación con la clave por defecto, el backend lo avisa por consola. Para generar una propia:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Frontend — `frontend/.env`

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Dirección de la API del backend |

Solo hay que tocarla si arranca el backend en otro puerto. El valor se incrusta al compilar, así que tras cambiarlo hay que reiniciar `npm run dev`.

---

## Solución de problemas

**`Error loading ASGI app. Could not import module "app.main"`.**
El módulo está mal escrito en el comando. El punto de entrada es `backend/main.py`, así que se escribe **`main:app`**, no `app.main`: la carpeta `app/` es el paquete con las cuatro capas, no el módulo de arranque. Desde `backend/`, el comando correcto es `uv run uvicorn main:app --reload --reload-exclude '.venv/*'`, o su atajo `uv run python main.py`.

**La consola se llena de `WatchFiles detected changes in '.venv/...'` y recarga sin parar.**
El recargador está vigilando el entorno virtual: cada archivo que `uv` escribe al instalar dependencias dispara una recarga. Lo evita `--reload-exclude '.venv/*'`, que ya viene en el comando de arranque.

**«No se pudo conectar con el servidor» al iniciar sesión.**
El backend no está en marcha o está en otro puerto. Compruebe con `curl http://localhost:8000/health`; debe responder `{"status":"healthy"}`.

**Error de CORS en la consola del navegador.**
Está abriendo la aplicación por una dirección que no figura en `CORS_ORIGINS`. Para el navegador, `localhost` y `127.0.0.1` son orígenes distintos: añada el que use a esa variable en `backend/.env` y reinicie el backend.

**«Email o contraseña incorrectos» con las cuentas de prueba.**
La base de datos está vacía. Ejecute `uv run python init_db.py` dentro de `backend/`.

**El puerto 8000 ya está ocupado.**
Arranque en otro puerto con `uv run uvicorn main:app --reload --port 8001` y ajuste `NEXT_PUBLIC_API_URL` en `frontend/.env`.

**Quiero empezar de cero.**
Borre `backend/labcloud.db` y vuelva a ejecutar `uv run python init_db.py`.

**«Debe estar en in_analysis para registrar un resultado».**
Es la máquina de estados haciendo su trabajo: la solicitud tiene que pasar antes por *en análisis*, y solo puede emitir el resultado el analista asignado.

---

## Limitaciones conocidas

Son decisiones conscientes, apropiadas para un prototipo académico pero no para producción:

- **SQLite** bloquea la base de datos entera en cada escritura, por lo que no admite escrituras concurrentes. La migración a PostgreSQL solo requiere cambiar `DATABASE_URL`, gracias al patrón Repository.
- **El bus de eventos es en memoria**: los eventos se pierden al reiniciar el proceso y no se propagan entre instancias. En un despliegue real se sustituiría por RabbitMQ o Kafka respetando la misma interfaz `subscribe`/`publish`.
- **No hay refresh tokens**: cuando el token caduca a los 30 minutos hay que volver a iniciar sesión.
- **No hay migraciones de esquema**: las tablas se crean con `create_all`. Un proyecto en producción usaría Alembic.
- **Sin caché, sin limitación de peticiones y sin registro centralizado.**
