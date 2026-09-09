"""Servicio de Resultados (capa de aplicacion)."""

from typing import Any

from app.core.events import NULL_EVENT_BUS, Event, EventBus, EventType
from app.domain.entities import DomainError, RequestStatus, Result
from app.domain.repositories import RequestRepository, ResultRepository


class ResultService:
    """Casos de uso relacionados con los resultados de analisis."""

    def __init__(
        self,
        result_repository: ResultRepository,
        request_repository: RequestRepository,
        event_bus: EventBus = NULL_EVENT_BUS,
    ) -> None:
        self.result_repository = result_repository
        self.request_repository = request_repository
        self.event_bus = event_bus

    def register_result(
        self,
        request_id: int,
        analyst_id: int,
        result_value: str,
        result_notes: str = "",
    ) -> Result:
        """Registra el resultado de una solicitud y la da por completada (RF-10).

        Todas las comprobaciones se hacen ANTES de escribir nada, para que no
        pueda quedar un resultado guardado con la solicitud sin cerrar. Ademas,
        como el commit lo realiza `get_db()` al final de la peticion, si algo
        fallara despues la transaccion completa se deshace.

        Raises:
            DomainError: Si la solicitud no existe, no esta en analisis, ya
                tiene resultado, o el analista no es el asignado.
        """
        request = self.request_repository.get_by_id(request_id)
        if not request:
            raise DomainError(f"Solicitud {request_id} no encontrada.")

        # Una solicitud solo puede completarse si esta en analisis.
        if request.status != RequestStatus.IN_ANALYSIS:
            raise DomainError(
                f"La solicitud {request.request_code} esta en estado "
                f"'{request.status.value}'. Debe estar en 'in_analysis' para "
                "registrar un resultado."
            )

        # Solo el analista asignado puede emitir el resultado.
        if request.assigned_analyst_id != analyst_id:
            raise DomainError(
                "Solo el analista asignado a la solicitud puede registrar su resultado."
            )

        if self.result_repository.get_by_request(request_id):
            raise DomainError(
                f"La solicitud {request.request_code} ya tiene un resultado registrado."
            )

        result = self.result_repository.save(
            Result(
                request_id=request_id,
                analyst_id=analyst_id,
                result_value=result_value,
                result_notes=result_notes,
            )
        )

        # Cerrar la solicitud forma parte del mismo caso de uso.
        request.change_status(RequestStatus.COMPLETED)
        self.request_repository.update(request)

        self.event_bus.publish(
            Event(
                EventType.RESULT_REGISTERED,
                {
                    "request_id": request_id,
                    "client_id": request.client_id,
                    "result_id": result.id,
                    "analyst_id": analyst_id,
                },
            )
        )
        return result

    def get_result(self, result_id: int) -> Result | None:
        """Devuelve un resultado por su id."""
        return self.result_repository.get_by_id(result_id)

    def get_result_by_request(self, request_id: int) -> Result | None:
        """Devuelve el resultado de una solicitud (RF-11)."""
        return self.result_repository.get_by_request(request_id)

    def get_all_results(self) -> list[Result]:
        """Devuelve todos los resultados (RF-11)."""
        return self.result_repository.get_all()

    def update_result(self, result_id: int, analyst_id: int, **changes: Any) -> Result:
        """Corrige un resultado ya emitido.

        Raises:
            DomainError: Si el resultado no existe o lo emitio otro analista.
        """
        result = self.result_repository.get_by_id(result_id)
        if not result:
            raise DomainError(f"Resultado {result_id} no encontrado.")

        if result.analyst_id != analyst_id:
            raise DomainError("Solo el analista que emitio el resultado puede modificarlo.")

        for key, value in changes.items():
            if value is not None and hasattr(result, key):
                setattr(result, key, value)
        return self.result_repository.update(result)
