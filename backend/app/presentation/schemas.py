"""Esquemas Pydantic (DTOs) de la capa de presentacion.

Definen el contrato publico de la API: que se acepta en cada peticion y que se
devuelve. Separarlos de las entidades del dominio permite, por ejemplo, no
exponer nunca el `password_hash` de un usuario.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.entities import RequestStatus, UserRole

# Configuracion comun de los DTOs de salida: `from_attributes` permite crear el
# esquema directamente desde una entidad del dominio.
ORM_CONFIG = ConfigDict(from_attributes=True)


# ===========================================================================
# Usuarios y autenticacion
# ===========================================================================


class UserRegister(BaseModel):
    """Alta publica desde la pantalla de registro.

    No incluye `role` a proposito: el registro publico siempre crea una cuenta
    de cliente. Solo un administrador puede crear cuentas con otros roles.
    """

    email: EmailStr
    password: str = Field(min_length=8, max_length=72, description="Minimo 8 caracteres")
    full_name: str = Field(min_length=3, max_length=255)


class UserCreate(UserRegister):
    """Alta de usuario realizada por un administrador, con rol explicito."""

    role: UserRole = UserRole.CLIENT


class UserLogin(BaseModel):
    """Credenciales de inicio de sesion."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Datos publicos de un usuario. Nunca incluye la contrasena."""

    model_config = ORM_CONFIG

    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class RoleUpdate(BaseModel):
    """Cambio de rol de un usuario."""

    role: UserRole


class ActiveUpdate(BaseModel):
    """Activacion o desactivacion de una cuenta."""

    is_active: bool


class TokenResponse(BaseModel):
    """Respuesta del inicio de sesion."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Vigencia del token en segundos")
    user_id: int
    email: str
    full_name: str
    role: UserRole


# ===========================================================================
# Clientes
# ===========================================================================


class ClientCreate(BaseModel):
    """Alta de un cliente del laboratorio."""

    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(default="", max_length=50)
    address: str = Field(default="", max_length=500)
    user_id: int | None = Field(
        default=None,
        description="Cuenta de acceso asociada, para que el cliente consulte sus resultados",
    )


class ClientUpdate(BaseModel):
    """Modificacion parcial de un cliente."""

    name: str | None = Field(default=None, min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    user_id: int | None = None


class ClientResponse(BaseModel):
    """Datos de un cliente."""

    model_config = ORM_CONFIG

    id: int
    name: str
    email: str
    phone: str
    address: str
    user_id: int | None = None
    created_at: datetime


# ===========================================================================
# Muestras
# ===========================================================================


class SampleCreate(BaseModel):
    """Registro de una muestra recibida."""

    sample_type: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=500)
    client_id: int
    sample_code: str | None = Field(
        default=None,
        max_length=50,
        description="Si se omite, el sistema genera un codigo unico",
    )


class SampleUpdate(BaseModel):
    """Modificacion parcial de una muestra."""

    sample_type: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class SampleResponse(BaseModel):
    """Datos de una muestra."""

    model_config = ORM_CONFIG

    id: int
    sample_code: str
    sample_type: str
    description: str
    client_id: int
    received_date: datetime
    created_at: datetime


# ===========================================================================
# Solicitudes
# ===========================================================================


class RequestCreate(BaseModel):
    """Alta de una solicitud de analisis."""

    client_id: int
    sample_id: int
    test_type: str = Field(min_length=2, max_length=255)


class RequestAssignAnalyst(BaseModel):
    """Asignacion de un analista a una solicitud."""

    analyst_id: int


class RequestStatusChange(BaseModel):
    """Cambio de estado de una solicitud."""

    status: RequestStatus


class RequestResponse(BaseModel):
    """Datos de una solicitud."""

    model_config = ORM_CONFIG

    id: int
    request_code: str
    client_id: int
    sample_id: int
    test_type: str
    status: RequestStatus
    assigned_analyst_id: int | None = None
    created_at: datetime
    updated_at: datetime


# ===========================================================================
# Resultados
# ===========================================================================


class ResultCreate(BaseModel):
    """Registro de un resultado.

    No lleva `analyst_id`: se toma del token del analista autenticado, para que
    nadie pueda firmar un resultado en nombre de otro.
    """

    request_id: int
    result_value: str = Field(min_length=1, max_length=2000)
    result_notes: str = Field(default="", max_length=2000)


class ResultUpdate(BaseModel):
    """Correccion de un resultado ya emitido."""

    result_value: str | None = Field(default=None, min_length=1, max_length=2000)
    result_notes: str | None = Field(default=None, max_length=2000)


class ResultResponse(BaseModel):
    """Datos de un resultado."""

    model_config = ORM_CONFIG

    id: int
    request_id: int
    analyst_id: int
    result_value: str
    result_notes: str
    created_at: datetime


# ===========================================================================
# Notificaciones
# ===========================================================================


class NotificationResponse(BaseModel):
    """Datos de una notificacion."""

    model_config = ORM_CONFIG

    id: int
    user_id: int
    request_id: int
    message: str
    is_read: bool
    created_at: datetime


# ===========================================================================
# Utilidades
# ===========================================================================


class MessageResponse(BaseModel):
    """Respuesta generica para operaciones sin cuerpo propio."""

    detail: str
