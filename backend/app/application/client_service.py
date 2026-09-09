"""Servicio de Clientes (capa de aplicacion)."""

from typing import Any

from app.core.events import NULL_EVENT_BUS, Event, EventBus, EventType
from app.domain.entities import Client, DomainError
from app.domain.repositories import ClientRepository


class ClientService:
    """Casos de uso relacionados con los clientes del laboratorio."""

    def __init__(
        self,
        repository: ClientRepository,
        event_bus: EventBus = NULL_EVENT_BUS,
    ) -> None:
        self.repository = repository
        self.event_bus = event_bus

    def create_client(
        self,
        name: str,
        email: str,
        phone: str = "",
        address: str = "",
        user_id: int | None = None,
    ) -> Client:
        """Registra un cliente nuevo (RF-04).

        Args:
            user_id: Cuenta de acceso asociada, si el cliente ya tiene una.

        Raises:
            DomainError: Si el email ya esta registrado.
        """
        email = email.strip().lower()
        if self.repository.get_by_email(email):
            raise DomainError(f"Ya existe un cliente con el email {email}.")

        client = self.repository.save(
            Client(
                name=name.strip(),
                email=email,
                phone=phone,
                address=address,
                user_id=user_id,
            )
        )

        self.event_bus.publish(
            Event(
                EventType.CLIENT_CREATED,
                {"client_id": client.id, "name": client.name, "email": client.email},
            )
        )
        return client

    def get_client(self, client_id: int) -> Client | None:
        """Devuelve un cliente por su id."""
        return self.repository.get_by_id(client_id)

    def get_client_by_user(self, user_id: int) -> Client | None:
        """Devuelve el cliente asociado a una cuenta de usuario.

        Es la pieza que permite que un usuario con rol `client` vea unicamente
        sus propias muestras, solicitudes y resultados.
        """
        return self.repository.get_by_user(user_id)

    def get_all_clients(self) -> list[Client]:
        """Devuelve todos los clientes."""
        return self.repository.get_all()

    def update_client(self, client_id: int, **changes: Any) -> Client:
        """Actualiza los datos de un cliente (RF-04).

        Raises:
            DomainError: Si el cliente no existe.
        """
        client = self.repository.get_by_id(client_id)
        if not client:
            raise DomainError(f"Cliente {client_id} no encontrado.")

        for key, value in changes.items():
            if value is not None and hasattr(client, key):
                setattr(client, key, value)
        return self.repository.update(client)

    def delete_client(self, client_id: int) -> bool:
        """Elimina un cliente. Devuelve False si no existia."""
        return self.repository.delete(client_id)
