# Arquitectura de LabCloud

Documento de diseño. Para instalar y ejecutar el proyecto, consulte `README.md`.

---

## 1. Principios

El sistema se organiza en **seis servicios** (usuarios, clientes, muestras, solicitudes, resultados y notificaciones) y cada uno se estructura internamente en **cuatro capas**. Las decisiones de diseño responden a cuatro principios:

**Separación de responsabilidades.** Cada servicio cubre un área del negocio y cada capa una preocupación técnica. Un cambio en la forma de guardar los datos no obliga a tocar las reglas de negocio.

**Dependencias hacia dentro.** El dominio no importa nada de FastAPI ni de SQLAlchemy. Depende de abstracciones que él mismo declara; son las capas externas las que dependen de él. Esto es lo que permite probar las reglas de negocio sin base de datos y cambiar de motor sin reescribir la lógica.

**Desacoplamiento por contratos.** Los servicios se comunican mediante interfaces explícitas y eventos, no mediante llamadas directas a las tripas de otro módulo.

**Escalabilidad preparada.** El diseño no es distribuido hoy, pero está estructurado para poder serlo: los límites entre servicios ya están trazados y la comunicación asíncrona pasa por una interfaz que puede respaldarse con una cola real.

---

## 2. Vista general

```
                    ┌───────────────────────────────┐
                    │      FRONTEND (Next.js)       │
                    │  Panel por rol · TypeScript   │
                    └───────────────┬───────────────┘
                                    │ HTTPS / REST + JWT
                    ┌───────────────▼───────────────┐
                    │     API GATEWAY (FastAPI)     │
                    │  CORS · Auth · Validación     │
                    │  Enrutado · Errores           │
                    └───┬───┬───┬───┬───┬───┬───────┘
                        │   │   │   │   │   │
        ┌───────────────┘   │   │   │   │   └───────────────┐
        │       ┌───────────┘   │   │   └───────────┐       │
        ▼       ▼               ▼   ▼               ▼       ▼
    ┌───────┐┌────────┐   ┌─────────┐┌──────────┐┌──────────────┐
    │Usuarios││Clientes│   │ Muestras││Solicitudes││  Resultados  │
    └───────┘└────────┘   └─────────┘└─────┬────┘└──────┬───────┘
                                            │            │
                                     publican eventos    │
                                            ▼            ▼
                                     ┌──────────────────────┐
                                     │   BUS DE EVENTOS     │
                                     └──────────┬───────────┘
                                                │ reacciona
                                     ┌──────────▼───────────┐
                                     │   Notificaciones     │
                                     └──────────┬───────────┘
                                                │
                    ┌───────────────────────────▼───────────────┐
                    │        SQLite  ·  6 tablas                │
                    │  users · clients · samples                │
                    │  requests · results · notifications       │
                    └───────────────────────────────────────────┘
```

---

## 3. Las cuatro capas

| Capa | Carpeta | Responsabilidad | Puede importar |
|---|---|---|---|
| Presentación | `app/presentation/` | Endpoints REST, validación de entrada, autenticación y RBAC | Aplicación, dominio |
| Aplicación | `app/application/` | Casos de uso, orquestación, publicación de eventos | Dominio, core |
| Dominio | `app/domain/` | Entidades, reglas de negocio, interfaces de repositorio | Nada del proyecto |
| Infraestructura | `app/infrastructure/` | ORM, base de datos, implementación de repositorios | Dominio, core |

`app/core/` contiene lo transversal: configuración, seguridad y el bus de eventos.

### Recorrido de una petición

Crear una solicitud de análisis (`POST /api/requests/`):

1. **Presentación** — `request_routes.create_request` recibe el JSON. Pydantic valida el cuerpo con `RequestCreate` y `require_staff` comprueba que quien llama es recepción o administración.
2. **Inyección** — `get_request_service` construye el servicio con sus cuatro repositorios y el bus de eventos, todos enlazados a la sesión de esta petición.
3. **Aplicación** — `RequestService.create_request` valida que existan cliente y muestra, y que la muestra pertenezca a ese cliente. Genera el código `SOL-AAAAMMDD-XXXXXX`.
4. **Dominio** — se construye la entidad `Request`, que nace en estado `PENDING`.
5. **Infraestructura** — `SQLAlchemyRequestRepository.save` traduce la entidad a la tabla y hace `flush()` para obtener el identificador. **No confirma la transacción.**
6. **Evento** — el servicio publica `REQUEST_CREATED`.
7. **Reacción** — el suscriptor de notificaciones resuelve qué usuario está detrás del cliente y crea el aviso, escribiendo en la misma sesión.
8. **Confirmación** — al terminar la petición, `get_db()` hace un único `commit`. Si cualquier paso hubiera fallado, no se guardaría nada.

---

## 4. Patrones aplicados

### API Gateway

`main.py` es el único punto de entrada. Centraliza CORS, monta los routers de los seis servicios y registra un manejador de excepciones que traduce `DomainError` a HTTP 400. Gracias a ese manejador, ni el dominio ni los servicios necesitan saber nada de HTTP, y las rutas quedan sin bloques `try/except` repetidos.

### Repository

El dominio declara en `app/domain/repositories.py` qué operaciones de persistencia necesita, mediante clases abstractas. La infraestructura las implementa con SQLAlchemy.

```
RequestService  ──►  RequestRepository (interfaz, en el dominio)
                             △
                             │ implementa
                     SQLAlchemyRequestRepository (infraestructura)
                             │
                             ▼
                          SQLite
```

La traducción entre modelo ORM y entidad se hace **campo a campo** en métodos `_to_entity`. No se copia `__dict__` de la instancia de SQLAlchemy porque ese diccionario incluye la clave interna `_sa_instance_state`, que rompería la construcción de la entidad.

### Unit of Work

La dependencia `get_db()` abre una sesión por petición, la entrega, y al terminar hace un único `commit`; ante cualquier excepción hace `rollback`. Por eso los repositorios usan `flush()` y nunca `commit()`.

Esto importa en operaciones compuestas. Registrar un resultado implica dos escrituras —guardar el resultado y cerrar la solicitud— que deben ocurrir juntas o no ocurrir. Con la confirmación en el repositorio, un fallo entre ambas dejaría un resultado huérfano con la solicitud sin cerrar.

### Event-Driven

`RequestService` y `ResultService` publican hechos; no saben que existen las notificaciones. `build_event_bus(session)` crea un bus por petición con los suscriptores enlazados por cierre a esa sesión, y lo inyecta en los servicios.

| Evento | Lo publica | Reacción |
|---|---|---|
| `REQUEST_CREATED` | `RequestService.create_request` | Aviso al cliente de que su solicitud quedó registrada |
| `REQUEST_STATUS_CHANGED` | `RequestService.change_status` | Aviso del nuevo estado |
| `REQUEST_ANALYST_ASSIGNED` | `RequestService.assign_analyst` | — (disponible para futuras reacciones) |
| `RESULT_REGISTERED` | `ResultService.register_result` | Aviso de que el resultado está disponible |
| `USER_CREATED` | `UserService.create_user` | — |
| `CLIENT_CREATED` | `ClientService.create_client` | — |

Si un suscriptor falla, el bus registra el error y continúa: un problema al notificar no debe tumbar la operación principal, que ya se completó.

**Por qué el bus se construye por petición y no como objeto global.** Un bus global con suscriptores registrados al arrancar necesitaría alguna forma de que los manejadores accedieran a la sesión de la petición en curso. Usar una variable de contexto (`ContextVar`) no funciona: FastAPI ejecuta las dependencias y los endpoints síncronos en un *threadpool*, y cada hilo recibe una **copia** del contexto, de modo que lo que se escribe allí no llega al endpoint y `reset()` falla con `ValueError: was created in a different Context`. La inyección explícita evita el problema por completo, es más fácil de seguir y hace trivial montar el bus en las pruebas.

### Inyección de dependencias

Todo el ensamblaje vive en `app/presentation/dependencies.py`: fábricas de servicios, autenticación y las guardas de rol. Ninguna ruta construye un repositorio por su cuenta.

### Máquina de estados

El ciclo de vida de la solicitud es una regla de negocio y por eso vive en la entidad `Request`, no en el servicio:

```
                 ┌──────────────┐
                 │   PENDING    │  ◄── estado inicial
                 └──┬────────┬──┘
                    │        │
                    ▼        ▼
          ┌──────────────┐  ┌───────────┐
          │ IN_ANALYSIS  │  │ CANCELLED │ ◄── final
          └──┬────────┬──┘  └───────────┘
             │        │           ▲
             ▼        └───────────┘
      ┌───────────┐
      │ COMPLETED │ ◄── final
      └───────────┘
```

`Request.change_status()` consulta `ALLOWED_STATUS_TRANSITIONS` y lanza `DomainError` si la transición no está permitida. El paso a `COMPLETED` no se expone en el endpoint de cambio de estado: se alcanza registrando el resultado, que es el hecho de negocio que realmente cierra la solicitud.

---

## 5. Modelo de datos

```sql
users (id, email UNIQUE, password_hash, full_name,
       role ENUM(admin|receptionist|analyst|client), is_active, created_at)

clients (id, name, email UNIQUE, phone, address,
         user_id → users.id UNIQUE NULL, created_at)

samples (id, sample_code UNIQUE, sample_type, description,
         client_id → clients.id, received_date, created_at)

requests (id, request_code UNIQUE, client_id → clients.id,
          sample_id → samples.id, test_type,
          status ENUM(pending|in_analysis|completed|cancelled),
          assigned_analyst_id → users.id NULL, created_at, updated_at)

results (id, request_id → requests.id UNIQUE, analyst_id → users.id,
         result_value, result_notes, created_at)

notifications (id, user_id → users.id, request_id → requests.id,
               message, is_read, created_at)
```

**`users` y `clients` son entidades distintas.** `users` representa a quien inicia sesión; `clients` a la clínica u hospital al que pertenece la muestra. Recepción puede dar de alta un cliente antes de que tenga cuenta, de ahí que `clients.user_id` sea opcional. Ese campo es la pieza que permite que un usuario con rol `client` vea solo su propia información, y también el destinatario correcto de las notificaciones.

**`results.request_id` es único.** Una solicitud tiene como mucho un resultado. La regla se valida en el servicio y además se refuerza con una restricción en la base de datos.

---

## 6. Seguridad

**Contraseñas.** Hash bcrypt con sal aleatoria por usuario, de modo que dos usuarios con la misma contraseña tienen hashes distintos. Se usa la biblioteca `bcrypt` directamente en lugar de `passlib`, porque esta última está sin mantenimiento y es incompatible con bcrypt ≥ 4.1.

**Tokens.** JWT firmado con HS256 y vigencia de 30 minutos. En cada petición se verifica la firma **y** se relee el usuario de la base de datos: si la cuenta fue eliminada o desactivada después de emitir el token, el acceso se corta de inmediato en lugar de confiar en unos *claims* caducados.

**Control de acceso.** La fábrica `require_roles(...)` genera una dependencia que comprueba el rol. Las combinaciones habituales tienen nombre propio (`require_admin`, `require_staff`, `require_analyst`, `require_lab_staff`) para que las rutas se lean como las reglas del enunciado.

**Aislamiento de datos.** Un usuario con rol `client` recibe listas filtradas por su ficha de cliente, y los accesos directos por identificador se comprueban antes de devolver nada.

**Decisiones defensivas concretas:**

- El registro público siempre crea rol `client`; los privilegiados los asigna un administrador.
- El `analyst_id` de un resultado se toma del token, nunca del cuerpo de la petición, para que nadie firme en nombre de otro.
- Solo el analista asignado puede emitir el resultado de una solicitud.
- El inicio de sesión devuelve el mismo mensaje si el correo no existe o si la contraseña es incorrecta, para no permitir enumerar cuentas registradas.
- Un administrador no puede desactivarse ni eliminarse a sí mismo.

**El frontend no es la barrera.** Ocultar un botón según el rol es una comodidad visual; quien decide de verdad es el backend, que valida token y rol en cada petición.

---

## 7. Estrategia de pruebas

| Nivel | Archivo | Qué cubre |
|---|---|---|
| Dominio | `tests/test_domain.py` | Máquina de estados, asignación de analista, roles, hash y tokens. Sin base de datos ni servidor. |
| Integración | `tests/test_api.py` | Aplicación completa contra SQLite en memoria: autenticación, RBAC, flujo del laboratorio, reglas de negocio vía API y aislamiento de datos por cliente. |

Que el primer bloque pueda escribirse sin ningún andamiaje es la comprobación práctica de que el dominio está realmente aislado.

Varias pruebas son **de regresión** y documentan defectos concretos ya corregidos: que la cabecera `Authorization` se lea de verdad, que `/api/requests/status/pending` no quede capturada por la ruta `/{request_id}`, y que `/api/users/analysts` no se interprete como un identificador.

---

## 8. Limitaciones y evolución

| Limitación actual | Camino de evolución |
|---|---|
| SQLite no admite escrituras concurrentes | Cambiar `DATABASE_URL` a PostgreSQL; el patrón Repository aísla el cambio |
| Bus de eventos en memoria y por proceso | RabbitMQ o Kafka manteniendo la interfaz `subscribe`/`publish` |
| Esquema creado con `create_all` | Migraciones versionadas con Alembic |
| Sin refresh tokens | Emitir un token de refresco de vida larga |
| Sin caché | Redis para sesiones y consultas frecuentes |
| Sin límite de peticiones | Rate limiting en el gateway |
| Sin trazas centralizadas | Registro estructurado y métricas con Prometheus |
| Despliegue manual | Contenedores con Docker Compose |

El paso a servicios realmente independientes no exigiría reescribir la lógica: los límites ya están trazados y cada servicio conversa con los demás a través de interfaces y eventos, no de llamadas internas.

---

*LabCloud v1.0.0 — Proyecto académico de Arquitectura de Software*
