"""Entidades del dominio.

Esta es la capa mas interna de la arquitectura: contiene los conceptos del
negocio y sus reglas. No importa nada de FastAPI, SQLAlchemy ni de ninguna
otra tecnologia, de modo que las reglas se pueden probar de forma aislada.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _now() -> datetime:
    """Marca de tiempo actual en UTC.

    Se centraliza aqui para no repetir `datetime.now(timezone.utc)` y para
    poder sustituirla facilmente en las pruebas.
    """
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    """Roles del sistema. Determinan que puede hacer cada usuario."""

    ADMIN = "admin"                # Administra usuarios y supervisa todo
    RECEPTIONIST = "receptionist"  # Registra clientes, muestras y solicitudes
    ANALYST = "analyst"            # Ejecuta analisis y registra resultados
    CLIENT = "client"              # Consulta sus solicitudes y resultados


class RequestStatus(str, Enum):
    """Estados por los que pasa una solicitud de analisis."""

    PENDING = "pending"          # Registrada, aun sin analizar
    IN_ANALYSIS = "in_analysis"  # Un analista la esta procesando
    COMPLETED = "completed"      # Tiene resultado registrado
    CANCELLED = "cancelled"      # Anulada


# Maquina de estados de una solicitud. Define la unica secuencia valida:
#   PENDING -> IN_ANALYSIS -> COMPLETED
# y permite cancelar mientras no se haya cerrado. Los estados finales
# (COMPLETED y CANCELLED) no admiten mas transiciones.
ALLOWED_STATUS_TRANSITIONS: dict[RequestStatus, list[RequestStatus]] = {
    RequestStatus.PENDING: [RequestStatus.IN_ANALYSIS, RequestStatus.CANCELLED],
    RequestStatus.IN_ANALYSIS: [RequestStatus.COMPLETED, RequestStatus.CANCELLED],
    RequestStatus.COMPLETED: [],
    RequestStatus.CANCELLED: [],
}


class DomainError(Exception):
    """Violacion de una regla de negocio.

    Las capas superiores la traducen a un codigo HTTP 400/409, de forma que el
    dominio nunca necesita conocer detalles del protocolo web.
    """


@dataclass
class User:
    """Usuario que accede al sistema."""

    id: int | None = None
    email: str = ""
    password_hash: str = ""
    full_name: str = ""
    role: UserRole = UserRole.CLIENT
    is_active: bool = True
    created_at: datetime = field(default_factory=_now)

    def has_role(self, *roles: UserRole) -> bool:
        """Indica si el usuario tiene alguno de los roles dados."""
        return self.role in roles


@dataclass
class Client:
    """Cliente del laboratorio (clinica, hospital o particular).

    `user_id` enlaza al cliente con la cuenta de acceso que consulta sus
    resultados. Es opcional porque recepcion puede dar de alta un cliente antes
    de que este tenga usuario.
    """

    id: int | None = None
    name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    user_id: int | None = None
    created_at: datetime = field(default_factory=_now)


@dataclass
class Sample:
    """Muestra fisica recibida en el laboratorio."""

    id: int | None = None
    sample_code: str = ""
    sample_type: str = ""
    description: str = ""
    client_id: int = 0
    received_date: datetime = field(default_factory=_now)
    created_at: datetime = field(default_factory=_now)


@dataclass
class Request:
    """Solicitud de analisis sobre una muestra.

    Es la entidad central del sistema y la unica que concentra una regla de
    negocio con estado: el ciclo de vida de la solicitud.
    """

    id: int | None = None
    request_code: str = ""
    client_id: int = 0
    sample_id: int = 0
    test_type: str = ""
    status: RequestStatus = RequestStatus.PENDING
    assigned_analyst_id: int | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def can_transition_to(self, new_status: RequestStatus) -> bool:
        """Indica si el cambio de estado solicitado es valido."""
        return new_status in ALLOWED_STATUS_TRANSITIONS[self.status]

    def change_status(self, new_status: RequestStatus) -> None:
        """Cambia el estado validando la maquina de estados.

        Raises:
            DomainError: Si la transicion no esta permitida.
        """
        if not self.can_transition_to(new_status):
            permitidos = [s.value for s in ALLOWED_STATUS_TRANSITIONS[self.status]] or ["ninguno"]
            raise DomainError(
                f"No se puede pasar de '{self.status.value}' a '{new_status.value}'. "
                f"Transiciones permitidas desde '{self.status.value}': {', '.join(permitidos)}."
            )
        self.status = new_status
        self.updated_at = _now()

    def assign_analyst(self, analyst_id: int) -> None:
        """Asigna un analista.

        Raises:
            DomainError: Si la solicitud ya esta cerrada.
        """
        if self.status in (RequestStatus.COMPLETED, RequestStatus.CANCELLED):
            raise DomainError(
                f"No se puede asignar un analista a una solicitud '{self.status.value}'."
            )
        self.assigned_analyst_id = analyst_id
        self.updated_at = _now()


@dataclass
class Result:
    """Resultado emitido por un analista para una solicitud."""

    id: int | None = None
    request_id: int = 0
    analyst_id: int = 0
    result_value: str = ""
    result_notes: str = ""
    created_at: datetime = field(default_factory=_now)


@dataclass
class Notification:
    """Aviso dirigido a un usuario sobre el avance de una solicitud."""

    id: int | None = None
    user_id: int = 0
    request_id: int = 0
    message: str = ""
    is_read: bool = False
    created_at: datetime = field(default_factory=_now)
