"""Suscriptores del bus de eventos.

Aqui se materializa la arquitectura dirigida por eventos: `RequestService` y
`ResultService` publican lo que ha ocurrido sin saber que existen las
notificaciones, y este modulo reacciona creandolas. Anadir una reaccion nueva
(un correo, una metrica) consiste en suscribir otro manejador, sin tocar los
servicios que publican.

El bus se construye una vez por peticion y sus manejadores quedan enlazados
mediante cierres a la sesion de esa peticion. Asi la notificacion se escribe
dentro de la misma transaccion que la operacion que la origino: si esta se
deshace, la notificacion tampoco queda guardada.
"""

import logging

from sqlalchemy.orm import Session

from app.application.notification_service import NotificationService
from app.core.events import Event, EventBus, EventType
from app.domain.entities import RequestStatus
from app.infrastructure.repositories import (
    SQLAlchemyClientRepository,
    SQLAlchemyNotificationRepository,
)

logger = logging.getLogger(__name__)


def build_event_bus(session: Session) -> EventBus:
    """Crea un bus con los suscriptores de notificaciones ya conectados.

    Args:
        session: Sesion de la peticion en curso, que usaran los manejadores.

    Returns:
        Un `EventBus` listo para que los servicios publiquen en el.
    """
    notifications = NotificationService(SQLAlchemyNotificationRepository(session))
    clients = SQLAlchemyClientRepository(session)

    def resolve_user_id(client_id: int | None) -> int | None:
        """Traduce el id de un cliente del laboratorio al de su cuenta de acceso.

        Son entidades distintas: `clients` guarda a quien pertenece la muestra y
        `users` a quien inicia sesion. Un cliente dado de alta por recepcion
        puede no tener cuenta todavia; en ese caso no hay a quien notificar.
        """
        if client_id is None:
            return None
        client = clients.get_by_id(client_id)
        if client is None:
            logger.debug("No se encontro el cliente %s al notificar", client_id)
            return None
        return client.user_id

    def on_request_created(event: Event) -> None:
        """Avisa al cliente de que su solicitud quedo registrada."""
        user_id = resolve_user_id(event.data.get("client_id"))
        if user_id:
            notifications.notify_status_change(
                user_id, event.data["request_id"], RequestStatus.PENDING
            )

    def on_request_status_changed(event: Event) -> None:
        """Avisa al cliente de cada cambio de estado de su solicitud (RF-13)."""
        user_id = resolve_user_id(event.data.get("client_id"))
        if not user_id:
            return
        try:
            nuevo_estado = RequestStatus(event.data["new_status"])
        except ValueError:
            logger.warning("Estado desconocido en el evento: %s", event.data.get("new_status"))
            return
        notifications.notify_status_change(user_id, event.data["request_id"], nuevo_estado)

    def on_result_registered(event: Event) -> None:
        """Avisa al cliente de que ya puede consultar su resultado."""
        user_id = resolve_user_id(event.data.get("client_id"))
        if user_id:
            notifications.create_notification(
                user_id,
                event.data["request_id"],
                "El resultado de su analisis ya esta disponible.",
            )

    bus = EventBus()
    bus.subscribe(EventType.REQUEST_CREATED, on_request_created)
    bus.subscribe(EventType.REQUEST_STATUS_CHANGED, on_request_status_changed)
    bus.subscribe(EventType.RESULT_REGISTERED, on_result_registered)
    return bus
