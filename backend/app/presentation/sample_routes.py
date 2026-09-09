"""Rutas de muestras de laboratorio."""


from fastapi import APIRouter, Depends, HTTPException, status

from app.application.sample_service import SampleService
from app.domain.entities import Sample, User, UserRole
from app.presentation.dependencies import (
    get_current_user,
    get_own_client_id,
    get_sample_service,
    require_staff,
)
from app.presentation.schemas import SampleCreate, SampleResponse, SampleUpdate

router = APIRouter(prefix="/api/samples", tags=["Muestras"])


def _assert_can_view_client_data(
    client_id: int,
    current_user: User,
    own_client_id: int | None,
) -> None:
    """Impide que un cliente consulte muestras que no son suyas."""
    if current_user.role == UserRole.CLIENT and own_client_id != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puede consultar sus propias muestras.",
        )


@router.post(
    "/",
    response_model=SampleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar muestra",
)
def create_sample(
    data: SampleCreate,
    _: User = Depends(require_staff),
    service: SampleService = Depends(get_sample_service),
) -> Sample:
    """Registra una muestra recibida en el laboratorio (RF-05).

    Si no se envia `sample_code`, el sistema genera uno unico.
    """
    return service.create_sample(
        sample_type=data.sample_type,
        description=data.description,
        client_id=data.client_id,
        sample_code=data.sample_code,
    )


@router.get("/", response_model=list[SampleResponse], summary="Listar muestras")
def list_samples(
    current_user: User = Depends(get_current_user),
    own_client_id: int | None = Depends(get_own_client_id),
    service: SampleService = Depends(get_sample_service),
) -> list[Sample]:
    """Devuelve las muestras visibles para el usuario.

    El personal del laboratorio ve todas; un cliente solo las suyas.
    """
    if current_user.role == UserRole.CLIENT:
        return service.get_samples_by_client(own_client_id) if own_client_id else []
    return service.get_all_samples()


# Ruta fija antes que `/{sample_id}`.
@router.get(
    "/client/{client_id}",
    response_model=list[SampleResponse],
    summary="Muestras de un cliente",
)
def list_samples_by_client(
    client_id: int,
    current_user: User = Depends(get_current_user),
    own_client_id: int | None = Depends(get_own_client_id),
    service: SampleService = Depends(get_sample_service),
) -> list[Sample]:
    """Devuelve las muestras de un cliente concreto."""
    _assert_can_view_client_data(client_id, current_user, own_client_id)
    return service.get_samples_by_client(client_id)


@router.get("/{sample_id}", response_model=SampleResponse, summary="Consultar muestra")
def get_sample(
    sample_id: int,
    current_user: User = Depends(get_current_user),
    own_client_id: int | None = Depends(get_own_client_id),
    service: SampleService = Depends(get_sample_service),
) -> Sample:
    """Devuelve una muestra concreta."""
    sample = service.get_sample(sample_id)
    if sample is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Muestra no encontrada.")

    _assert_can_view_client_data(sample.client_id, current_user, own_client_id)
    return sample


@router.put("/{sample_id}", response_model=SampleResponse, summary="Actualizar muestra")
def update_sample(
    sample_id: int,
    data: SampleUpdate,
    _: User = Depends(require_staff),
    service: SampleService = Depends(get_sample_service),
) -> Sample:
    """Modifica los datos descriptivos de una muestra."""
    return service.update_sample(sample_id, **data.model_dump(exclude_unset=True))
