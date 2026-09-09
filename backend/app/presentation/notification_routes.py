"""Rutas de notificaciones."""


from fastapi import APIRouter, Depends, HTTPException, status

from app.application.notification_service import NotificationService
from app.domain.entities import Notification, User, UserRole
from app.presentation.dependencies import (
    get_current_user,
    get_notification_service,
    require_admin,
)
from app.presentation.schemas import NotificationResponse

router = APIRouter(prefix="/api/notifications", tags=["Notificaciones"])


@router.get(
    "/",
    response_model=list[NotificationResponse],
    summary="Todas las notificaciones (solo administrador)",
)
def list_all_notifications(
    _: User = Depends(require_admin),
    service: NotificationService = Depends(get_notification_service),
) -> list[Notification]:
    """Devuelve las notificaciones de todo el sistema."""
    return service.get_all_notifications()


# Ruta fija antes que `/user/{user_id}` no hace falta, pero `/mine` si debe ir
# antes de cualquier patron dinamico del mismo nivel.
@router.get(
    "/mine",
    response_model=list[NotificationResponse],
    summary="Mis notificaciones",
)
def list_my_notifications(
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> list[Notification]:
    """Devuelve las notificaciones del usuario autenticado (RF-13)."""
    return service.get_user_notifications(current_user.id)


@router.get(
    "/user/{user_id}",
    response_model=list[NotificationResponse],
    summary="Notificaciones de un usuario",
)
def list_user_notifications(
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> list[Notification]:
    """Devuelve las notificaciones de un usuario (RF-13).

    Cada usuario ve solo las suyas; el administrador puede ver las de cualquiera.
    """
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puede consultar sus propias notificaciones.",
        )
    return service.get_user_notifications(user_id)


@router.put(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Marcar notificacion como leida",
)
def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> Notification:
    """Marca como leida una notificacion propia."""
    notification = service.get_notification(notification_id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notificacion no encontrada."
        )

    # Sin esta comprobacion, cualquier usuario autenticado podria marcar como
    # leidas las notificaciones de otro simplemente probando identificadores.
    if notification.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puede marcar sus propias notificaciones.",
        )

    return service.mark_as_read(notification_id)
