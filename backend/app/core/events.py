"""Bus de eventos en memoria (patron Event-Driven).

Permite que un servicio avise de algo que ha ocurrido sin conocer a quien le
interesa. Por ejemplo, `RequestService` publica `REQUEST_CREATED` y el modulo
de notificaciones reacciona creando el aviso al cliente, sin que exista ninguna
dependencia directa entre ambos.

Limitacion asumida: al ser en memoria, los eventos se pierden si el proceso se
reinicia. En un despliegue real se sustituiria por RabbitMQ o Kafka
respetando esta misma interfaz (`subscribe` / `publish`).
"""

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Eventos de dominio que publica el sistema."""

    REQUEST_CREATED = "request_created"
    REQUEST_STATUS_CHANGED = "request_status_changed"
    REQUEST_ANALYST_ASSIGNED = "request_analyst_assigned"
    RESULT_REGISTERED = "result_registered"
    USER_CREATED = "user_created"
    CLIENT_CREATED = "client_created"


@dataclass(frozen=True)
class Event:
    """Hecho ocurrido en el dominio.

    Es inmutable a proposito: un evento describe algo que ya paso y por tanto
    ningun suscriptor deberia poder modificarlo.
    """

    event_type: EventType
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = field(default_factory=lambda: uuid4().hex)

    def to_dict(self) -> dict[str, Any]:
        """Representacion serializable del evento (util para trazas y logs)."""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


# Un manejador es cualquier funcion que recibe el evento y no devuelve nada.
EventHandler = Callable[[Event], None]


class EventBus:
    """Publicador/suscriptor sencillo y sincrono."""

    # Numero maximo de eventos que se conservan para inspeccion.
    MAX_HISTORY = 200

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._history: list[Event] = []

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Registra un manejador para un tipo de evento."""
        self._handlers[event_type].append(handler)
        logger.debug("Suscrito %s a %s", getattr(handler, "__name__", handler), event_type.value)

    def publish(self, event: Event) -> None:
        """Entrega el evento a todos sus suscriptores.

        Si un manejador falla se registra el error y se continua con el resto:
        un fallo al notificar no debe tumbar la operacion principal que ya se
        completo correctamente.
        """
        self._remember(event)
        for handler in self._handlers[event.event_type]:
            try:
                handler(event)
            except Exception:  # noqa: BLE001 - aislamos al publicador de sus suscriptores
                logger.exception("Fallo el manejador del evento %s", event.event_type.value)

    def get_events_log(self) -> list[dict[str, Any]]:
        """Devuelve los ultimos eventos publicados, del mas reciente al mas antiguo."""
        return [event.to_dict() for event in reversed(self._history)]

    def clear(self) -> None:
        """Vacia suscriptores e historial. Se usa entre pruebas."""
        self._handlers.clear()
        self._history.clear()

    def _remember(self, event: Event) -> None:
        """Guarda el evento en el historial acotado."""
        self._history.append(event)
        if len(self._history) > self.MAX_HISTORY:
            del self._history[: -self.MAX_HISTORY]


# Bus sin suscriptores. Se usa como valor por defecto para poder instanciar un
# servicio de forma aislada (por ejemplo en una prueba unitaria) sin tener que
# montar el sistema de eventos: publicar en el simplemente no hace nada.
NULL_EVENT_BUS = EventBus()
