"""Dependencias compartidas de la capa de presentacion.

Concentra dos responsabilidades transversales que antes estaban repartidas y
duplicadas por cada archivo de rutas:

1. **Inyeccion de dependencias**: construye los servicios de aplicacion con sus
   repositorios ya enlazados a la sesion de la peticion.
2. **Autenticacion y autorizacion**: valida el token JWT y comprueba el rol,
   mediante la fabrica `require_roles(...)` que se reutiliza en cada endpoint.

El esquema de seguridad se declara con `HTTPBearer`, de modo que FastAPI lee de
verdad la cabecera `Authorization: Bearer <token>` y ademas Swagger muestra el
boton "Authorize" para probar la API desde el navegador.
"""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.application.client_service import ClientService
from app.application.event_handlers import build_event_bus
from app.application.notification_service import NotificationService
from app.application.request_service import RequestService
from app.application.result_service import ResultService
from app.application.sample_service import SampleService
from app.application.user_service import UserService
from app.core.events import EventBus
from app.core.security import TokenError, decode_token
from app.domain.entities import User, UserRole
from app.infrastructure.database import get_db
from app.infrastructure.repositories import (
    SQLAlchemyClientRepository,
    SQLAlchemyNotificationRepository,
    SQLAlchemyRequestRepository,
    SQLAlchemyResultRepository,
    SQLAlchemySampleRepository,
    SQLAlchemyUserRepository,
)

# `auto_error=False` permite devolver un mensaje propio en espanol cuando falta
# la cabecera, en lugar del texto por defecto de FastAPI.
bearer_scheme = HTTPBearer(auto_error=False, description="Token JWT obtenido en /api/auth/login")


# ---------------------------------------------------------------------------
# Fabricas de servicios (inyeccion de dependencias)
# ---------------------------------------------------------------------------


def get_event_bus(db: Session = Depends(get_db)) -> EventBus:
    """Construye el bus de eventos de la peticion.

    Sus suscriptores quedan enlazados a esta misma sesion, de forma que las
    notificaciones que generen formen parte de la misma transaccion.
    """
    return build_event_bus(db)


def get_user_service(
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
) -> UserService:
    """Construye el servicio de usuarios."""
    return UserService(SQLAlchemyUserRepository(db), bus)


def get_client_service(
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
) -> ClientService:
    """Construye el servicio de clientes."""
    return ClientService(SQLAlchemyClientRepository(db), bus)


def get_sample_service(db: Session = Depends(get_db)) -> SampleService:
    """Construye el servicio de muestras."""
    return SampleService(SQLAlchemySampleRepository(db), SQLAlchemyClientRepository(db))


def get_request_service(
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
) -> RequestService:
    """Construye el servicio de solicitudes."""
    return RequestService(
        SQLAlchemyRequestRepository(db),
        SQLAlchemyClientRepository(db),
        SQLAlchemySampleRepository(db),
        SQLAlchemyUserRepository(db),
        bus,
    )


def get_result_service(
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
) -> ResultService:
    """Construye el servicio de resultados."""
    return ResultService(
        SQLAlchemyResultRepository(db), SQLAlchemyRequestRepository(db), bus
    )


def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    """Construye el servicio de notificaciones."""
    return NotificationService(SQLAlchemyNotificationRepository(db))


# ---------------------------------------------------------------------------
# Autenticacion
# ---------------------------------------------------------------------------


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """Valida el token y devuelve el usuario autenticado.

    Ademas de comprobar la firma, se relee el usuario de la base de datos. Asi,
    si la cuenta fue eliminada o desactivada despues de emitir el token, el
    acceso se deniega de inmediato en vez de confiar en unos claims caducados.

    Raises:
        HTTPException 401: Token ausente, invalido, expirado o cuenta inactiva.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporciono el token de autorizacion.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token no identifica a ningun usuario.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_service.get_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El usuario del token ya no existe.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta esta desactivada.",
        )
    return user


# ---------------------------------------------------------------------------
# Autorizacion basada en roles (RBAC)
# ---------------------------------------------------------------------------


def require_roles(*roles: UserRole) -> Callable[..., User]:
    """Crea una dependencia que exige alguno de los roles indicados.

    Ejemplo de uso en una ruta:

        @router.post("/")
        def crear(usuario: User = Depends(require_roles(UserRole.ADMIN))):
            ...

    Returns:
        Una dependencia que devuelve el usuario si tiene permiso.
    """

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.has_role(*roles):
            permitidos = ", ".join(r.value for r in roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Esta accion requiere uno de estos roles: {permitidos}.",
            )
        return current_user

    return dependency


# Combinaciones de roles usadas con frecuencia, con nombre propio para que las
# rutas se lean como las reglas del enunciado.
require_admin = require_roles(UserRole.ADMIN)
require_analyst = require_roles(UserRole.ANALYST)
require_staff = require_roles(UserRole.ADMIN, UserRole.RECEPTIONIST)
require_lab_staff = require_roles(UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.ANALYST)


def get_own_client_id(
    current_user: User = Depends(get_current_user),
    client_service: ClientService = Depends(get_client_service),
) -> int | None:
    """Devuelve el cliente asociado al usuario autenticado, si lo tiene.

    Solo es relevante para el rol `client`: sirve para filtrar los listados de
    forma que cada cliente vea unicamente su propia informacion.
    """
    client = client_service.get_client_by_user(current_user.id)
    return client.id if client else None
