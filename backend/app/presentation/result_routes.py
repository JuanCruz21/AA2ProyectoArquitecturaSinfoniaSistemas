"""Rutas de resultados de analisis."""


from fastapi import APIRouter, Depends, HTTPException, status

from app.application.request_service import RequestService
from app.application.result_service import ResultService
from app.domain.entities import Result, User, UserRole
from app.presentation.dependencies import (
    get_current_user,
    get_own_client_id,
    get_request_service,
    get_result_service,
    require_analyst,
)
from app.presentation.schemas import ResultCreate, ResultResponse, ResultUpdate

router = APIRouter(prefix="/api/results", tags=["Resultados"])


def _assert_can_view(
    result: Result,
    current_user: User,
    own_client_id: int | None,
    request_service: RequestService,
) -> None:
    """Comprueba que el usuario puede ver ese resultado.

    Un cliente solo accede al resultado de sus propias solicitudes, para lo cual
    hay que consultar la solicitud a la que pertenece.
    """
    if current_user.role in (UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.ANALYST):
        return

    request = request_service.get_request(result.request_id)
    if request is None or request.client_id != own_client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para consultar este resultado.",
        )


@router.post(
    "/",
    response_model=ResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar resultado (solo analista)",
)
def register_result(
    data: ResultCreate,
    analyst: User = Depends(require_analyst),
    service: ResultService = Depends(get_result_service),
) -> Result:
    """Registra el resultado de una solicitud y la da por completada (RF-10).

    El identificador del analista se toma del token, nunca del cuerpo de la
    peticion: asi ningun analista puede firmar un resultado en nombre de otro.
    """
    return service.register_result(
        request_id=data.request_id,
        analyst_id=analyst.id,
        result_value=data.result_value,
        result_notes=data.result_notes,
    )


@router.get("/", response_model=list[ResultResponse], summary="Listar resultados")
def list_results(
    current_user: User = Depends(get_current_user),
    own_client_id: int | None = Depends(get_own_client_id),
    service: ResultService = Depends(get_result_service),
    request_service: RequestService = Depends(get_request_service),
) -> list[Result]:
    """Devuelve los resultados visibles para el usuario (RF-11).

    Un cliente recibe unicamente los resultados de sus propias solicitudes.
    """
    if current_user.role != UserRole.CLIENT:
        return service.get_all_results()

    if own_client_id is None:
        return []

    # Ids de las solicitudes del cliente, para filtrar sus resultados.
    propias = {r.id for r in request_service.get_requests_by_client(own_client_id)}
    return [r for r in service.get_all_results() if r.request_id in propias]


# Ruta fija antes que `/{result_id}`.
@router.get(
    "/request/{request_id}",
    response_model=ResultResponse,
    summary="Resultado de una solicitud",
)
def get_result_by_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    own_client_id: int | None = Depends(get_own_client_id),
    service: ResultService = Depends(get_result_service),
    request_service: RequestService = Depends(get_request_service),
) -> Result:
    """Devuelve el resultado asociado a una solicitud (RF-11)."""
    result = service.get_result_by_request(request_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Esta solicitud aun no tiene resultado registrado.",
        )

    _assert_can_view(result, current_user, own_client_id, request_service)
    return result


@router.get("/{result_id}", response_model=ResultResponse, summary="Consultar resultado")
def get_result(
    result_id: int,
    current_user: User = Depends(get_current_user),
    own_client_id: int | None = Depends(get_own_client_id),
    service: ResultService = Depends(get_result_service),
    request_service: RequestService = Depends(get_request_service),
) -> Result:
    """Devuelve un resultado concreto."""
    result = service.get_result(result_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resultado no encontrado."
        )

    _assert_can_view(result, current_user, own_client_id, request_service)
    return result


@router.put(
    "/{result_id}",
    response_model=ResultResponse,
    summary="Corregir resultado (solo el analista que lo emitio)",
)
def update_result(
    result_id: int,
    data: ResultUpdate,
    analyst: User = Depends(require_analyst),
    service: ResultService = Depends(get_result_service),
) -> Result:
    """Corrige un resultado ya emitido."""
    return service.update_result(
        result_id,
        analyst_id=analyst.id,
        **data.model_dump(exclude_unset=True),
    )
