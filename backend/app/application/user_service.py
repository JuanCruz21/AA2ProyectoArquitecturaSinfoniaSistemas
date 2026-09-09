"""Servicio de Usuarios y Autenticacion (capa de aplicacion).

Coordina los casos de uso de alta, autenticacion y gestion de roles. No
contiene reglas de negocio propias del dominio ni detalles de persistencia:
orquesta al dominio, al repositorio y a las utilidades de seguridad.
"""

from typing import Any

from app.core.config import settings
from app.core.events import NULL_EVENT_BUS, Event, EventBus, EventType
from app.core.security import create_access_token, hash_password, verify_password
from app.domain.entities import DomainError, User, UserRole
from app.domain.repositories import UserRepository


class UserService:
    """Casos de uso relacionados con usuarios."""

    def __init__(
        self,
        repository: UserRepository,
        event_bus: EventBus = NULL_EVENT_BUS,
    ) -> None:
        self.repository = repository
        # El bus se recibe por inyeccion. Su valor por defecto no tiene
        # suscriptores, de modo que el servicio se puede instanciar suelto en
        # una prueba unitaria sin montar el sistema de eventos.
        self.event_bus = event_bus

    def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
        role: UserRole = UserRole.CLIENT,
    ) -> User:
        """Registra un usuario nuevo (RF-01).

        Raises:
            DomainError: Si el email ya existe o la contrasena es demasiado corta.
        """
        if len(password) < settings.min_password_length:
            raise DomainError(
                f"La contrasena debe tener al menos {settings.min_password_length} caracteres."
            )

        email = email.strip().lower()
        if self.repository.get_by_email(email):
            raise DomainError(f"Ya existe un usuario registrado con el email {email}.")

        user = self.repository.save(
            User(
                email=email,
                password_hash=hash_password(password),
                full_name=full_name.strip(),
                role=role,
            )
        )

        self.event_bus.publish(
            Event(
                EventType.USER_CREATED,
                {"user_id": user.id, "email": user.email, "role": user.role.value},
            )
        )
        return user

    def authenticate(self, email: str, password: str) -> dict[str, Any] | None:
        """Valida las credenciales y devuelve el token de acceso (RF-02).

        Returns:
            El token y los datos basicos del usuario, o None si las credenciales
            no son correctas. Se devuelve None tanto si el email no existe como
            si la contrasena falla, para no revelar cuales estan registrados.

        Raises:
            DomainError: Si el usuario existe pero esta desactivado.
        """
        user = self.repository.get_by_email(email.strip().lower())
        if not user or not verify_password(password, user.password_hash):
            return None

        if not user.is_active:
            raise DomainError("La cuenta esta desactivada. Contacte con el administrador.")

        token = create_access_token(
            {"sub": user.email, "user_id": user.id, "role": user.role.value}
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
        }

    def get_user(self, user_id: int) -> User | None:
        """Devuelve un usuario por su id."""
        return self.repository.get_by_id(user_id)

    def get_all_users(self) -> list[User]:
        """Devuelve todos los usuarios registrados."""
        return self.repository.get_all()

    def get_analysts(self) -> list[User]:
        """Devuelve los usuarios con rol de analista.

        Lo usa recepcion para elegir a quien asignar una solicitud.
        """
        return [u for u in self.repository.get_all() if u.role == UserRole.ANALYST]

    def update_user(self, user_id: int, **changes: Any) -> User:
        """Actualiza los datos de un usuario.

        La clave `password` recibe la contrasena en claro y se guarda hasheada.

        Raises:
            DomainError: Si el usuario no existe.
        """
        user = self._require_user(user_id)
        for key, value in changes.items():
            if value is None:
                continue
            if key == "password":
                user.password_hash = hash_password(value)
            elif hasattr(user, key):
                setattr(user, key, value)
        return self.repository.update(user)

    def assign_role(self, user_id: int, role: UserRole) -> User:
        """Cambia el rol de un usuario (RF-03).

        Raises:
            DomainError: Si el usuario no existe.
        """
        user = self._require_user(user_id)
        user.role = role
        return self.repository.update(user)

    def set_active(self, user_id: int, is_active: bool) -> User:
        """Activa o desactiva una cuenta sin borrar su historial.

        Raises:
            DomainError: Si el usuario no existe.
        """
        user = self._require_user(user_id)
        user.is_active = is_active
        return self.repository.update(user)

    def delete_user(self, user_id: int) -> bool:
        """Elimina un usuario. Devuelve False si no existia."""
        return self.repository.delete(user_id)

    def _require_user(self, user_id: int) -> User:
        """Recupera un usuario o lanza un error de dominio si no existe."""
        user = self.repository.get_by_id(user_id)
        if not user:
            raise DomainError(f"Usuario {user_id} no encontrado.")
        return user
