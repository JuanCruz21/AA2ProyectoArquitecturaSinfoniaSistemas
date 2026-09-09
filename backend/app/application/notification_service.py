"""Servicio de Notificaciones (capa de aplicacion)."""


from app.domain.entities import DomainError, Notification, RequestStatus
from app.domain.repositories import NotificationRepository

# Texto que ve el cliente para cada estado de su solicitud. Tenerlo en un unico
# diccionario evita que los mensajes se dupliquen por el codigo.
STATUS_MESSAGES = {
    RequestStatus.PENDING: "Su solicitud ha sido registrada.",
    RequestStatus.IN_ANALYSIS: "Su solicitud esta siendo analizada.",
    RequestStatus.COMPLETED: "Su solicitud ha finalizado. Los resultados ya estan disponibles.",
    RequestStatus.CANCELLED: "Su solicitud ha sido cancelada.",
}


class NotificationService:
    """Casos de uso relacionados con los avisos a los usuarios."""

    def __init__(self, notification_repository: NotificationRepository) -> None:
        self.notification_repository = notification_repository

    def create_notification(self, user_id: int, request_id: int, message: str) -> Notification:
        """Crea una notificacion para un usuario."""
        return self.notification_repository.save(
            Notification(user_id=user_id, request_id=request_id, message=message)
        )

    def notify_status_change(
        self,
        user_id: int,
        request_id: int,
        new_status: RequestStatus,
    ) -> Notification:
        """Avisa al usuario del nuevo estado de su solicitud (RF-13)."""
        message = STATUS_MESSAGES.get(new_status, f"Su solicitud cambio a '{new_status.value}'.")
        return self.create_notification(user_id, request_id, message)

    def get_user_notifications(self, user_id: int) -> list[Notification]:
        """Devuelve las notificaciones de un usuario (RF-13)."""
        return self.notification_repository.get_by_user(user_id)

    def get_all_notifications(self) -> list[Notification]:
        """Devuelve todas las notificaciones del sistema."""
        return self.notification_repository.get_all()

    def get_notification(self, notification_id: int) -> Notification | None:
        """Devuelve una notificacion por su id."""
        return self.notification_repository.get_by_id(notification_id)

    def mark_as_read(self, notification_id: int) -> Notification:
        """Marca una notificacion como leida.

        Raises:
            DomainError: Si la notificacion no existe.
        """
        notification = self.notification_repository.mark_as_read(notification_id)
        if not notification:
            raise DomainError(f"Notificacion {notification_id} no encontrada.")
        return notification
