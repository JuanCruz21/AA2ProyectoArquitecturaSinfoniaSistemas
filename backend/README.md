# LabCloud · Backend

API REST del sistema de gestión de análisis de laboratorio. Python con FastAPI, SQLAlchemy y SQLite.

Para la visión de conjunto del proyecto consulte el `README.md` de la raíz; para el diseño en detalle, `ARQUITECTURA.md`.

---

## Arrancar

```bash
uv sync --extra dev          # instala dependencias y crea .venv
uv run python init_db.py     # crea la base de datos con datos de prueba
uv run uvicorn main:app --reload
```

La API queda en http://localhost:8000 y la documentación interactiva en http://localhost:8000/docs.

El archivo `.env` ya viene incluido con valores de desarrollo, así que no hace falta configurar nada para empezar. `.env.example` es la plantilla de referencia.

---

## Cuentas de prueba

Las crea `init_db.py`. Contraseña común: **`password123`**.

| Rol | Correo |
|---|---|
| Administrador | `admin@labcloud.com` |
| Recepcionista | `recepcion@labcloud.com` |
| Analista | `analista@labcloud.com` |
| Cliente | `cliente@labcloud.com` |

---

## Comandos

| Qué hace | Comando |
|---|---|
| Instalar dependencias | `uv sync --extra dev` |
| Cargar datos de prueba | `uv run python init_db.py` |
| Arrancar en desarrollo | `uv run uvicorn main:app --reload` |
| Ejecutar las pruebas | `uv run pytest -v` |
| Revisar el código | `uv run ruff check .` |
| Corregir lo automatizable | `uv run ruff check --fix .` |
| Empezar de cero | `rm labcloud.db && uv run python init_db.py` |

---

## Estructura

```
backend/
├── main.py              Punto de entrada · API Gateway · manejo de errores
├── init_db.py           Carga de datos de prueba
├── pyproject.toml       Dependencias y configuración de pytest y ruff
├── .env                 Configuración local (lista para usar)
├── .env.example         Plantilla de configuración
│
├── app/
│   ├── core/            Configuración, seguridad (bcrypt + JWT), bus de eventos
│   ├── domain/          Entidades, reglas de negocio e interfaces de repositorio
│   ├── application/     Servicios de caso de uso y suscriptores de eventos
│   ├── infrastructure/  Modelos SQLAlchemy, sesión y repositorios
│   └── presentation/    Esquemas Pydantic, dependencias y routers REST
│
└── tests/
    ├── test_domain.py   Reglas de negocio puras (sin base de datos)
    └── test_api.py      Integración: autenticación, RBAC y flujo completo
```

Las capas dependen siempre hacia dentro: `presentation → application → domain`, y la infraestructura implementa las interfaces que declara el dominio. `app/domain/` no importa nada de FastAPI ni de SQLAlchemy.

---

## Pruebas

```bash
uv run pytest -v
```

43 pruebas en total. `test_domain.py` cubre la máquina de estados de la solicitud, los roles y la seguridad sin necesidad de base de datos ni servidor; `test_api.py` recorre la aplicación entera contra SQLite en memoria.

---

## Configuración

Variables de `.env`:

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `APP_NAME` | `LabCloud API` | Nombre en la documentación |
| `DEBUG` | `True` | Recarga automática y registro detallado |
| `DATABASE_URL` | `sqlite:///./labcloud.db` | Conexión a la base de datos |
| `SECRET_KEY` | *(clave de desarrollo)* | Firma de los tokens JWT |
| `ALGORITHM` | `HS256` | Algoritmo de firma |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Vigencia del token |
| `MIN_PASSWORD_LENGTH` | `8` | Longitud mínima de contraseña |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Orígenes autorizados |

`CORS_ORIGINS` admite tanto una lista separada por comas como JSON.

---

## Notas de implementación

**Transacciones.** `get_db()` confirma una sola vez al final de cada petición y deshace todo si algo falla (Unit of Work). Por eso los repositorios usan `flush()` y nunca `commit()`.

**Eventos.** El bus se construye por petición en `dependencies.get_event_bus` con los suscriptores enlazados a esa sesión. Se hace así, y no con un bus global, porque FastAPI ejecuta las dependencias síncronas en un *threadpool* y cada hilo recibe una copia del contexto, de modo que una `ContextVar` no llegaría al endpoint.

**Orden de las rutas.** FastAPI resuelve por orden de declaración, así que los patrones fijos (`/mine`, `/analysts`, `/status/{estado}`) se declaran antes que los dinámicos (`/{id}`).

**Contraseñas.** Se usa `bcrypt` directamente en lugar de `passlib`, que está sin mantenimiento y es incompatible con bcrypt ≥ 4.1.
