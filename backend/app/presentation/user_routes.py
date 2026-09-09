"""Rutas de gestion de usuarios (reservadas al administrador)."""


from fastapi import APIRouter, Depends, HTTPException, status

from app.application.user_service import UserService
from app.domain.entities import User
from app.presentation.dependencies import (
    get_current_user,
    get_user_service,
    require_admin,
    require_staff,
)
from app.presentation.schemas import (
    ActiveUpdate,
    MessageResponse,
    RoleUpdate,
    UserCreate,
    UserResponse,
)

router = APIRouter(prefix="/api/users", tags=["Usuarios"])


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario con rol (solo administrador)",
)
def create_user(
    data: UserCreate,
    _: User = Depends(require_admin),
    service: UserService = Depends(get_user_service),
) -> User:
    """Da de alta un usuario con el rol indicado (RF-01)."""
    return service.create_user(
        email=data.email,
        password=data.password,
        full_name=data.full_name,
        role=data.role,
    )


@router.get(
    "/",
    response_model=list[UserResponse],
    summary="Listar usuarios (solo administrador)",
)
def list_users(
    _: User = Depends(require_admin),
    service: UserService = Depends(get_user_service),
) -> list[User]:
    """Devuelve todos los usuarios registrados."""
    return service.get_all_users()


# Esta ruta se declara ANTES que `/{user_id}`. FastAPI resuelve las rutas en el
# orden en que se registran, asi que un patron fijo como `/analysts` debe ir
# primero o quedaria capturado por el parametro dinamico.
@router.get(
    "/analysts",
    response_model=list[UserResponse],
    summary="Listar analistas disponibles",
)
def list_analysts(
    _: User = Depends(require_staff),
    service: UserService = Depends(get_user_service),
) -> list[User]:
    """Devuelve los usuarios con rol de analista, para poder asignarlos (RF-08)."""
    return service.get_analysts()


@router.get("/{user_id}", response_model=UserResponse, summary="Consultar un usuario")
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> User:
    """Devuelve un usuario concreto.

    Cualquiera puede consultar su propio perfil; el resto de fichas solo las ve
    un administrador.
    """
    if current_user.id != user_id and current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puede consultar su propio perfil.",
        )

    user = service.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    return user


@router.put(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Asignar rol (solo administrador)",
)
def assign_role(
    user_id: int,
    data: RoleUpdate,
    _: User = Depends(require_admin),
    service: UserService = Depends(get_user_service),
) -> User:
    """Cambia el rol de un usuario (RF-03)."""
    return service.assign_role(user_id, data.role)


@router.put(
    "/{user_id}/active",
    response_model=UserResponse,
    summary="Activar o desactivar una cuenta (solo administrador)",
)
def set_active(
    user_id: int,
    data: ActiveUpdate,
    admin: User = Depends(require_admin),
    service: UserService = Depends(get_user_service),
) -> User:
    """Habilita o deshabilita el acceso de un usuario sin borrar su historial."""
    if admin.id == user_id and not data.is_active:
        # Evita que el administrador se bloquee a si mismo el acceso.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede desactivar su propia cuenta.",
        )
    return service.set_active(user_id, data.is_active)


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Eliminar usuario (solo administrador)",
)
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    service: UserService = Depends(get_user_service),
) -> MessageResponse:
    """Elimina definitivamente un usuario."""
    if admin.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede eliminar su propia cuenta.",
        )
    if not service.delete_user(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    return MessageResponse(detail="Usuario eliminado.")
