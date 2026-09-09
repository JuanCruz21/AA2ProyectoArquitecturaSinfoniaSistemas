"""Rutas de autenticacion: registro, inicio de sesion y perfil."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.user_service import UserService
from app.domain.entities import User, UserRole
from app.presentation.dependencies import get_current_user, get_user_service
from app.presentation.schemas import (
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)

router = APIRouter(prefix="/api/auth", tags=["Autenticacion"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una cuenta de cliente",
)
def register(
    data: UserRegister,
    service: UserService = Depends(get_user_service),
) -> User:
    """Crea una cuenta nueva (RF-01).

    El registro publico siempre genera un usuario con rol `client`. Las cuentas
    de recepcion, analista o administrador las crea un administrador desde
    `POST /api/users/`, para que nadie pueda auto-asignarse privilegios.
    """
    return service.create_user(
        email=data.email,
        password=data.password,
        full_name=data.full_name,
        role=UserRole.CLIENT,
    )


@router.post("/login", response_model=TokenResponse, summary="Iniciar sesion")
def login(
    credentials: UserLogin,
    service: UserService = Depends(get_user_service),
) -> dict:
    """Valida las credenciales y devuelve un token JWT (RF-02)."""
    session_data = service.authenticate(credentials.email, credentials.password)
    if session_data is None:
        # Mismo mensaje para email inexistente y contrasena erronea: revelar
        # cual de los dos fallo facilitaria enumerar usuarios registrados.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contrasena incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return session_data


@router.get("/me", response_model=UserResponse, summary="Perfil del usuario autenticado")
def get_profile(current_user: User = Depends(get_current_user)) -> User:
    """Devuelve los datos del usuario dueno del token."""
    return current_user
