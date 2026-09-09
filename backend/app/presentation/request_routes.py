"""Rutas de solicitudes de analisis.

IMPORTANTE sobre el orden de declaracion: FastAPI evalua las rutas en el orden
en que se registran. Por eso `/mine`, `/client/{id}`, `/analyst/{id}` y
`/status/{estado}` se declaran ANTES de `/{request_id}`. Si `/{request_id}`
fuera primero, una URL como `/api/requests/status/pending` intentaria
interpretar "status" como un identificador numerico y devolveria un error 422.
"""


from fastapi import APIRouter, Depends, HTTPException, status

from app.application.request_service import RequestService
from app.domain.entities import Request, RequestStatus, User, UserRole
from app.presentation.dependencies import (
    get_current_user,
    get_own_client_id,
    get_request_service,
    require_lab_staff,
    require_staff,
)
from app.presentation.schemas import (
    RequestAssignAnalyst,
    RequestCreate,
    RequestResponse,
    RequestStatusChange,
)

router = APIRouter(prefix="/api/requests", tags=["Solicitudes"])


def _assert_can_view(
    request: Request,
    current_user: User,
    own_client_id: int | None,
) -> None:
    """Comprueba que el usuario puede ver esa solicitud.

    Administracion y recepcion ven todas; un analista ve las que tiene
    asignadas; un cliente solo las suyas.
    """
    if current_user.role in (UserRole.ADMIN, UserRole.RECEPTIONIST):
        return
    if current_user.role == UserRole.ANALYST and request.assigned_analyst_id == current_user.id:
        return
    if current_user.role == UserRole.CLIENT and request.client_id == own_client_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tiene permiso para consultar esta solicitud.",
    )


@router.post(
    "/",
    response_model=RequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear solicitud de analisis",
)
def create_request(
    data: RequestCreate,
    _: User = Depends(require_staff),
    service: RequestService = Depends(get_request_service),
) -> Request:
    """Crea una solicitud de analisis (RF-06).

    La notificacion al cliente no se genera aqui: el servicio publica el evento
    `REQUEST_CREATED` y el suscriptor de notificaciones reacciona a el.
    """
    return service.create_request(
        client_id=data.client_id,
        sample_id=data.sample_id,
        test_type=data.test_type,
    )


@router.get("/", response_model=list[RequestResponse], summary="Listar solicitudes")
def list_requests(
    current_user: User = Depends(get_current_user),
    own_client_id: int | None = Depends(get_own_client_id),
    service: RequestService = Depends(get_request_service),
) -> list[Request]:
    """Devuelve las solicitudes visibles segun el rol del usuario."""
    if current_user.role in (UserRole.ADMIN, UserRole.RECEPTIONIST):
        return service.get_all_requests()
    if current_user.role == UserRole.ANALYST:
        return service.get_requests_by_analyst(current_user.id)
    return service.get_requests_by_client(own_client_id) if own_client_id else []


@router.get(
    "/mine",
    response_model=list[RequestResponse],
    summary="Mis solicitudes (cliente o analista)",
)
def list_my_requests(
    current_user: User = Depends(get_current_user),
    own_client_id: int | None = Depends(get_own_client_id),
    service: RequestService = Depends(get_request_service),
) -> list[Request]:
    """Atajo para el panel del usuario.

    Un analista obtiene las solicitudes que tiene asignadas (RF-09) y un cliente
    las suyas (RF-14).
    """
    if current_user.role == UserRole.ANALYST:
        return service.get_requests_by_analyst(current_user.id)
    if current_user.role == UserRole.CLIENT:
        return service.get_requests_by_client(own_client_id) if own_client_id else []
    return service.get_all_requests()


@router.get(
    "/status/{request_status}",
    response_model=list[RequestResponse],
    summary="Solicitudes por estado",
)
def list_requests_by_status(
    request_status: RequestStatus,
    _: User = Depends(require_lab_staff),
    service: RequestService = Depends(get_request_service),
) -> list[Request]:
    """Devuelve las solicitudes que estan en un estado dado.

    FastAPI valida el valor contra el enum, asi que un estado inexistente
    devuelve 422 sin llegar al servicio.
    """
    return service.get_requests_by_status(request_status)


@router.get(
    "/client/{client_id}",
    response_model=list[RequestResponse],
    summary="Solicitudes de un cliente",
)
def list_requests_by_client(
    client_id: int,
    current_user: User = Depends(get_current_user),
    own_client_id: int | None = Depends(get_own_client_id),
    service: RequestService = Depends(get_request_service),
) -> list[Request]:
    """Devuelve las solicitudes de un cliente (RF-07, RF-14)."""
    if current_user.role == UserRole.CLIENT and own_client_id != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puede consultar sus propias solicitudes.",
        )
    return service.get_requests_by_client(client_id)


@router.get(
    "/analyst/{analyst_id}",
    response_model=list[RequestResponse],
    summary="Solicitudes asignadas a un analista",
)
def list_requests_by_analyst(
    analyst_id: int,
    current_user: User = Depends(get_current_user),
    service: RequestService = Depends(get_request_service),
) -> list[Request]:
    """Devuelve las solicitudes asignadas a un analista (RF-09).

    Un analista solo puede consultar su propia carga de trabajo; recepcion y
    administracion pueden consultar la de cualquiera.
    """
    if current_user.role == UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para consultar la carga de los analistas.",
        )
    if current_user.role == UserRole.ANALYST and current_user.id != analyst_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puede consultar las solicitudes que tiene asignadas.",
        )
    return service.get_requests_by_analyst(analyst_id)


@router.get("/{request_id}", response_model=RequestResponse, summary="Consultar solicitud")
def get_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    own_client_id: int | None = Depends(get_own_client_id),
    service: RequestService = Depends(get_request_service),
) -> Request:
    """Devuelve una solicitud concreta (RF-07)."""
    request = service.get_request(request_id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud no encontrada."
        )

    _assert_can_view(request, current_user, own_client_id)
    return request


@router.put(
    "/{request_id}/analyst",
    response_model=RequestResponse,
    summary="Asignar analista a una solicitud",
)
def assign_analyst(
    request_id: int,
    data: RequestAssignAnalyst,
    _: User = Depends(require_staff),
    service: RequestService = Depends(get_request_service),
) -> Request:
    """Asigna un analista responsable de la solicitud (RF-08)."""
    return service.assign_analyst(request_id, data.analyst_id)


@router.put(
    "/{request_id}/status",
    response_model=RequestResponse,
    summary="Cambiar el estado de una solicitud",
)
def change_status(
    request_id: int,
    data: RequestStatusChange,
    current_user: User = Depends(require_lab_staff),
    service: RequestService = Depends(get_request_service),
) -> Request:
    """Cambia el estado de una solicitud respetando la maquina de estados.

    Un analista solo puede mover las solicitudes que tiene asignadas; recepcion
    y administracion pueden mover cualquiera. La transicion a `completed` no se
    hace por aqui, sino registrando el resultado en `POST /api/results/`.
    """
    request = service.get_request(request_id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud no encontrada."
        )

    if (
        current_user.role == UserRole.ANALYST
        and request.assigned_analyst_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puede modificar las solicitudes que tiene asignadas.",
        )

    if data.status == RequestStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Una solicitud se completa registrando su resultado en "
                "POST /api/results/, no cambiando el estado directamente."
            ),
        )

    return service.change_status(request_id, data.status)
