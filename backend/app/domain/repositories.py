"""Interfaces de repositorio (patron Repository).

El dominio declara *que* necesita para persistir sus entidades, pero no *como*
se hace. La implementacion concreta con SQLAlchemy vive en la capa de
infraestructura. Gracias a esta inversion de dependencias se puede cambiar
SQLite por PostgreSQL, o por un repositorio en memoria en las pruebas, sin
tocar ni el dominio ni los servicios de aplicacion.
"""

from abc import ABC, abstractmethod

from app.domain.entities import (
    Client,
    Notification,
    Request,
    RequestStatus,
    Result,
    Sample,
    User,
)


class UserRepository(ABC):
    """Persistencia de usuarios."""

    @abstractmethod
    def save(self, user: User) -> User:
        """Inserta el usuario y devuelve la entidad con su `id` asignado."""

    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None:
        """Devuelve el usuario con ese id, o None si no existe."""

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        """Devuelve el usuario con ese email, o None si no existe."""

    @abstractmethod
    def get_all(self) -> list[User]:
        """Devuelve todos los usuarios."""

    @abstractmethod
    def update(self, user: User) -> User:
        """Guarda los cambios de un usuario existente."""

    @abstractmethod
    def delete(self, user_id: int) -> bool:
        """Elimina el usuario. Devuelve True si existia."""


class ClientRepository(ABC):
    """Persistencia de clientes del laboratorio."""

    @abstractmethod
    def save(self, client: Client) -> Client:
        """Inserta el cliente y devuelve la entidad con su `id` asignado."""

    @abstractmethod
    def get_by_id(self, client_id: int) -> Client | None:
        """Devuelve el cliente con ese id, o None si no existe."""

    @abstractmethod
    def get_by_email(self, email: str) -> Client | None:
        """Devuelve el cliente con ese email, o None si no existe."""

    @abstractmethod
    def get_by_user(self, user_id: int) -> Client | None:
        """Devuelve el cliente asociado a una cuenta de usuario."""

    @abstractmethod
    def get_all(self) -> list[Client]:
        """Devuelve todos los clientes."""

    @abstractmethod
    def update(self, client: Client) -> Client:
        """Guarda los cambios de un cliente existente."""

    @abstractmethod
    def delete(self, client_id: int) -> bool:
        """Elimina el cliente. Devuelve True si existia."""


class SampleRepository(ABC):
    """Persistencia de muestras."""

    @abstractmethod
    def save(self, sample: Sample) -> Sample:
        """Inserta la muestra y devuelve la entidad con su `id` asignado."""

    @abstractmethod
    def get_by_id(self, sample_id: int) -> Sample | None:
        """Devuelve la muestra con ese id, o None si no existe."""

    @abstractmethod
    def get_by_code(self, sample_code: str) -> Sample | None:
        """Devuelve la muestra con ese codigo, o None si no existe."""

    @abstractmethod
    def get_by_client(self, client_id: int) -> list[Sample]:
        """Devuelve las muestras de un cliente."""

    @abstractmethod
    def get_all(self) -> list[Sample]:
        """Devuelve todas las muestras."""

    @abstractmethod
    def update(self, sample: Sample) -> Sample:
        """Guarda los cambios de una muestra existente."""


class RequestRepository(ABC):
    """Persistencia de solicitudes de analisis."""

    @abstractmethod
    def save(self, request: Request) -> Request:
        """Inserta la solicitud y devuelve la entidad con su `id` asignado."""

    @abstractmethod
    def get_by_id(self, request_id: int) -> Request | None:
        """Devuelve la solicitud con ese id, o None si no existe."""

    @abstractmethod
    def get_by_client(self, client_id: int) -> list[Request]:
        """Devuelve las solicitudes de un cliente."""

    @abstractmethod
    def get_by_analyst(self, analyst_id: int) -> list[Request]:
        """Devuelve las solicitudes asignadas a un analista."""

    @abstractmethod
    def get_by_status(self, status: RequestStatus) -> list[Request]:
        """Devuelve las solicitudes que estan en un estado dado."""

    @abstractmethod
    def get_all(self) -> list[Request]:
        """Devuelve todas las solicitudes."""

    @abstractmethod
    def update(self, request: Request) -> Request:
        """Guarda los cambios de una solicitud existente."""


class ResultRepository(ABC):
    """Persistencia de resultados de analisis."""

    @abstractmethod
    def save(self, result: Result) -> Result:
        """Inserta el resultado y devuelve la entidad con su `id` asignado."""

    @abstractmethod
    def get_by_id(self, result_id: int) -> Result | None:
        """Devuelve el resultado con ese id, o None si no existe."""

    @abstractmethod
    def get_by_request(self, request_id: int) -> Result | None:
        """Devuelve el resultado de una solicitud, o None si aun no existe."""

    @abstractmethod
    def get_all(self) -> list[Result]:
        """Devuelve todos los resultados."""

    @abstractmethod
    def update(self, result: Result) -> Result:
        """Guarda los cambios de un resultado existente."""


class NotificationRepository(ABC):
    """Persistencia de notificaciones."""

    @abstractmethod
    def save(self, notification: Notification) -> Notification:
        """Inserta la notificacion y devuelve la entidad con su `id`."""

    @abstractmethod
    def get_by_id(self, notification_id: int) -> Notification | None:
        """Devuelve la notificacion con ese id, o None si no existe."""

    @abstractmethod
    def get_by_user(self, user_id: int) -> list[Notification]:
        """Devuelve las notificaciones de un usuario, de la mas reciente a la mas antigua."""

    @abstractmethod
    def mark_as_read(self, notification_id: int) -> Notification | None:
        """Marca la notificacion como leida. Devuelve None si no existe."""

    @abstractmethod
    def get_all(self) -> list[Notification]:
        """Devuelve todas las notificaciones."""
