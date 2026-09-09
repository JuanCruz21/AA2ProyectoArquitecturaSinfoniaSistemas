"""Servicio de Solicitudes de analisis (capa de aplicacion).

Es el servicio central del sistema. Orquesta el ciclo de vida de una solicitud
apoyandose en la maquina de estados que vive en la entidad `Request`, y publica
eventos para que otros modulos (notificaciones) reaccionen sin acoplarse.
"""

from datetime import datetime, timezone
from uuid import uuid4

from app.core.events import NULL_EVENT_BUS, Event, EventBus, EventType
from app.domain.entities import DomainError, Request, RequestStatus, UserRole
from app.domain.repositories import (
    ClientRepository,
    RequestRepository,
    SampleRepository,
    UserRepository,
)


class RequestService:
    """Casos de uso del ciclo de vida de una solicitud de analisis."""

    def __init__(
        self,
        request_repository: RequestRepository,
        client_repository: ClientRepository,
        sample_repository: SampleRepository,
        user_repository: UserRepository,
        event_bus: EventBus = NULL_EVENT_BUS,
    ) -> None:
        self.request_repository = request_repository
        self.client_repository = client_repository
        self.sample_repository = sample_repository
        self.user_repository = user_repository
        self.event_bus = event_bus

    @staticmethod
    def generate_request_code() -> str:
        """Genera un codigo de solicitud unico con formato `SOL-AAAAMMDD-XXXXXX`."""
        fecha = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"SOL-{fecha}-{uuid4().hex[:6].upper()}"

    def create_request(self, client_id: int, sample_id: int, test_type: str) -> Request:
        """Crea una solicitud de analisis (RF-06).

        Raises:
            DomainError: Si el cliente o la muestra no existen, o si la muestra
                pertenece a otro cliente.
        """
        if not self.client_repository.get_by_id(client_id):
            raise DomainError(f"Cliente {client_id} no encontrado.")

        sample = self.sample_repository.get_by_id(sample_id)
        if not sample:
            raise DomainError(f"Muestra {sample_id} no encontrada.")

        # Coherencia del dominio: no tiene sentido analizar la muestra de un
        # cliente en nombre de otro.
        if sample.client_id != client_id:
            raise DomainError(
                f"La muestra {sample.sample_code} pertenece a otro cliente."
            )

        request = self.request_repository.save(
            Request(
                request_code=self.generate_request_code(),
                client_id=client_id,
                sample_id=sample_id,
                test_type=test_type.strip(),
                status=RequestStatus.PENDING,
            )
        )

        self.event_bus.publish(
            Event(
                EventType.REQUEST_CREATED,
                {
                    "request_id": request.id,
                    "request_code": request.request_code,
                    "client_id": client_id,
                },
            )
        )
        return request

    def get_request(self, request_id: int) -> Request | None:
        """Devuelve una solicitud por su id (RF-07)."""
        return self.request_repository.get_by_id(request_id)

    def get_requests_by_client(self, client_id: int) -> list[Request]:
        """Devuelve las solicitudes de un cliente (RF-14)."""
        return self.request_repository.get_by_client(client_id)

    def get_requests_by_analyst(self, analyst_id: int) -> list[Request]:
        """Devuelve las solicitudes asignadas a un analista (RF-09)."""
        return self.request_repository.get_by_analyst(analyst_id)

    def get_requests_by_status(self, status: RequestStatus) -> list[Request]:
        """Devuelve las solicitudes que estan en un estado dado."""
        return self.request_repository.get_by_status(status)

    def get_all_requests(self) -> list[Request]:
        """Devuelve todas las solicitudes."""
        return self.request_repository.get_all()

    def assign_analyst(self, request_id: int, analyst_id: int) -> Request:
        """Asigna un analista a la solicitud (RF-08).

        Raises:
            DomainError: Si la solicitud no existe, si el usuario indicado no es
                analista, o si la solicitud ya esta cerrada.
        """
        request = self._require_request(request_id)

        analyst = self.user_repository.get_by_id(analyst_id)
        if not analyst or analyst.role != UserRole.ANALYST:
            raise DomainError(f"El usuario {analyst_id} no es un analista valido.")

        # La validacion del estado la hace la propia entidad.
        request.assign_analyst(analyst_id)
        updated = self.request_repository.update(request)

        self.event_bus.publish(
            Event(
                EventType.REQUEST_ANALYST_ASSIGNED,
                {
                    "request_id": request_id,
                    "client_id": request.client_id,
                    "analyst_id": analyst_id,
                },
            )
        )
        return updated

    def change_status(self, request_id: int, new_status: RequestStatus) -> Request:
        """Cambia el estado de una solicitud validando la maquina de estados.

        Raises:
            DomainError: Si la solicitud no existe o la transicion no es valida.
        """
        request = self._require_request(request_id)
        previous_status = request.status

        # La regla de negocio esta en la entidad, no aqui.
        request.change_status(new_status)
        updated = self.request_repository.update(request)

        self.event_bus.publish(
            Event(
                EventType.REQUEST_STATUS_CHANGED,
                {
                    "request_id": request_id,
                    "client_id": request.client_id,
                    "old_status": previous_status.value,
                    "new_status": new_status.value,
                },
            )
        )
        return updated

    def start_analysis(self, request_id: int) -> Request:
        """Atajo para pasar la solicitud a 'en analisis'."""
        return self.change_status(request_id, RequestStatus.IN_ANALYSIS)

    def cancel_request(self, request_id: int) -> Request:
        """Atajo para cancelar una solicitud."""
        return self.change_status(request_id, RequestStatus.CANCELLED)

    def _require_request(self, request_id: int) -> Request:
        """Recupera una solicitud o lanza un error de dominio si no existe."""
        request = self.request_repository.get_by_id(request_id)
        if not request:
            raise DomainError(f"Solicitud {request_id} no encontrada.")
        return request
