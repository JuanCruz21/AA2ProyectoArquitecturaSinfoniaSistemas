"""Rutas de clientes del laboratorio."""


from fastapi import APIRouter, Depends, HTTPException, status

from app.application.client_service import ClientService
from app.domain.entities import Client, User, UserRole
from app.presentation.dependencies import (
    get_client_service,
    get_current_user,
    get_own_client_id,
    require_admin,
    require_staff,
)
from app.presentation.schemas import (
    ClientCreate,
    ClientResponse,
    ClientUpdate,
    MessageResponse,
)

router = APIRouter(prefix="/api/clients", tags=["Clientes"])


def _assert_can_view(client_id: int, current_user: User, own_client_id: int | None) -> None:
    """Comprueba que el usuario puede ver la ficha de ese cliente.

    El personal del laboratorio ve todas las fichas; un usuario con rol
    `client` solo la suya.
    """
    if current_user.role != UserRole.CLIENT:
        return
    if own_client_id != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puede consultar su propia ficha de cliente.",
        )


@router.post(
    "/",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar cliente",
)
def create_client(
    data: ClientCreate,
    _: User = Depends(require_staff),
    service: ClientService = Depends(get_client_service),
) -> Client:
    """Da de alta un cliente del laboratorio (RF-04)."""
    return service.create_client(
        name=data.name,
        email=data.email,
        phone=data.phone,
        address=data.address,
        user_id=data.user_id,
    )


@router.get("/", response_model=list[ClientResponse], summary="Listar clientes")
def list_clients(
    current_user: User = Depends(get_current_user),
    own_client_id: int | None = Depends(get_own_client_id),
    service: ClientService = Depends(get_client_service),
) -> list[Client]:
    """Devuelve los clientes visibles para el usuario.

    Un usuario con rol `client` recibe unicamente su propia ficha, de forma que
    el listado no filtre datos de otros clientes del laboratorio.
    """
    if current_user.role == UserRole.CLIENT:
        client = service.get_client(own_client_id) if own_client_id else None
        return [client] if client else []
    return service.get_all_clients()


# Ruta fija declarada antes que `/{client_id}` para que no la capture el
# parametro dinamico.
@router.get("/me", response_model=ClientResponse, summary="Ficha del cliente autenticado")
def get_my_client(
    own_client_id: int | None = Depends(get_own_client_id),
    service: ClientService = Depends(get_client_service),
) -> Client:
    """Devuelve la ficha de cliente asociada a la cuenta que hace la peticion."""
    client = service.get_client(own_client_id) if own_client_id else None
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Su cuenta no esta asociada a ninguna ficha de cliente.",
        )
    return client


@router.get("/{client_id}", response_model=ClientResponse, summary="Consultar cliente")
def get_client(
    client_id: int,
    current_user: User = Depends(get_current_user),
    own_client_id: int | None = Depends(get_own_client_id),
    service: ClientService = Depends(get_client_service),
) -> Client:
    """Devuelve la ficha de un cliente."""
    _assert_can_view(client_id, current_user, own_client_id)

    client = service.get_client(client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")
    return client


@router.put("/{client_id}", response_model=ClientResponse, summary="Actualizar cliente")
def update_client(
    client_id: int,
    data: ClientUpdate,
    _: User = Depends(require_staff),
    service: ClientService = Depends(get_client_service),
) -> Client:
    """Modifica los datos de un cliente (RF-04)."""
    return service.update_client(client_id, **data.model_dump(exclude_unset=True))


@router.delete(
    "/{client_id}",
    response_model=MessageResponse,
    summary="Eliminar cliente (solo administrador)",
)
def delete_client(
    client_id: int,
    _: User = Depends(require_admin),
    service: ClientService = Depends(get_client_service),
) -> MessageResponse:
    """Elimina un cliente del laboratorio."""
    if not service.delete_client(client_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")
    return MessageResponse(detail="Cliente eliminado.")
