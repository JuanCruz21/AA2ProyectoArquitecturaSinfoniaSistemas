"""Implementacion de los repositorios con SQLAlchemy.

Cada clase traduce entre el modelo ORM (tabla) y la entidad del dominio. El
mapeo se hace campo a campo de forma explicita en lugar de copiar `__dict__`:
el diccionario de una instancia de SQLAlchemy incluye la clave interna
`_sa_instance_state`, que rompe la construccion de la entidad.

Los metodos de escritura usan `flush()` y no `commit()`. El commit lo hace la
dependencia `get_db()` al terminar la peticion (Unit of Work), de manera que
varias escrituras de un mismo caso de uso son atomicas.
"""


from sqlalchemy.orm import Session

from app.domain.entities import (
    Client,
    Notification,
    Request,
    RequestStatus,
    Result,
    Sample,
    User,
)
from app.domain.repositories import (
    ClientRepository,
    NotificationRepository,
    RequestRepository,
    ResultRepository,
    SampleRepository,
    UserRepository,
)
from app.infrastructure.database import (
    ClientModel,
    NotificationModel,
    RequestModel,
    ResultModel,
    SampleModel,
    UserModel,
)


class _BaseRepository:
    """Comportamiento comun: guardar la sesion recibida por inyeccion."""

    def __init__(self, db: Session) -> None:
        self.db = db


# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------


class SQLAlchemyUserRepository(_BaseRepository, UserRepository):
    """Repositorio de usuarios sobre SQLAlchemy."""

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        """Convierte una fila de `users` en la entidad `User`."""
        return User(
            id=model.id,
            email=model.email,
            password_hash=model.password_hash,
            full_name=model.full_name,
            role=model.role,
            is_active=model.is_active,
            created_at=model.created_at,
        )

    def save(self, user: User) -> User:
        model = UserModel(
            email=user.email,
            password_hash=user.password_hash,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        )
        self.db.add(model)
        self.db.flush()  # Fuerza el INSERT para obtener el id autogenerado.
        user.id = model.id
        return user

    def get_by_id(self, user_id: int) -> User | None:
        model = self.db.get(UserModel, user_id)
        return self._to_entity(model) if model else None

    def get_by_email(self, email: str) -> User | None:
        model = self.db.query(UserModel).filter(UserModel.email == email).first()
        return self._to_entity(model) if model else None

    def get_all(self) -> list[User]:
        return [self._to_entity(m) for m in self.db.query(UserModel).order_by(UserModel.id).all()]

    def update(self, user: User) -> User:
        model = self.db.get(UserModel, user.id)
        if model is None:
            raise ValueError(f"Usuario {user.id} no encontrado")
        model.email = user.email
        model.password_hash = user.password_hash
        model.full_name = user.full_name
        model.role = user.role
        model.is_active = user.is_active
        self.db.flush()
        return user

    def delete(self, user_id: int) -> bool:
        model = self.db.get(UserModel, user_id)
        if model is None:
            return False
        self.db.delete(model)
        self.db.flush()
        return True


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------


class SQLAlchemyClientRepository(_BaseRepository, ClientRepository):
    """Repositorio de clientes sobre SQLAlchemy."""

    @staticmethod
    def _to_entity(model: ClientModel) -> Client:
        """Convierte una fila de `clients` en la entidad `Client`."""
        return Client(
            id=model.id,
            name=model.name,
            email=model.email,
            phone=model.phone,
            address=model.address,
            user_id=model.user_id,
            created_at=model.created_at,
        )

    def save(self, client: Client) -> Client:
        model = ClientModel(
            name=client.name,
            email=client.email,
            phone=client.phone,
            address=client.address,
            user_id=client.user_id,
            created_at=client.created_at,
        )
        self.db.add(model)
        self.db.flush()
        client.id = model.id
        return client

    def get_by_id(self, client_id: int) -> Client | None:
        model = self.db.get(ClientModel, client_id)
        return self._to_entity(model) if model else None

    def get_by_email(self, email: str) -> Client | None:
        model = self.db.query(ClientModel).filter(ClientModel.email == email).first()
        return self._to_entity(model) if model else None

    def get_by_user(self, user_id: int) -> Client | None:
        model = self.db.query(ClientModel).filter(ClientModel.user_id == user_id).first()
        return self._to_entity(model) if model else None

    def get_all(self) -> list[Client]:
        return [
            self._to_entity(m) for m in self.db.query(ClientModel).order_by(ClientModel.id).all()
        ]

    def update(self, client: Client) -> Client:
        model = self.db.get(ClientModel, client.id)
        if model is None:
            raise ValueError(f"Cliente {client.id} no encontrado")
        model.name = client.name
        model.email = client.email
        model.phone = client.phone
        model.address = client.address
        model.user_id = client.user_id
        self.db.flush()
        return client

    def delete(self, client_id: int) -> bool:
        model = self.db.get(ClientModel, client_id)
        if model is None:
            return False
        self.db.delete(model)
        self.db.flush()
        return True


# ---------------------------------------------------------------------------
# Muestras
# ---------------------------------------------------------------------------


class SQLAlchemySampleRepository(_BaseRepository, SampleRepository):
    """Repositorio de muestras sobre SQLAlchemy."""

    @staticmethod
    def _to_entity(model: SampleModel) -> Sample:
        """Convierte una fila de `samples` en la entidad `Sample`."""
        return Sample(
            id=model.id,
            sample_code=model.sample_code,
            sample_type=model.sample_type,
            description=model.description,
            client_id=model.client_id,
            received_date=model.received_date,
            created_at=model.created_at,
        )

    def save(self, sample: Sample) -> Sample:
        model = SampleModel(
            sample_code=sample.sample_code,
            sample_type=sample.sample_type,
            description=sample.description,
            client_id=sample.client_id,
            received_date=sample.received_date,
            created_at=sample.created_at,
        )
        self.db.add(model)
        self.db.flush()
        sample.id = model.id
        return sample

    def get_by_id(self, sample_id: int) -> Sample | None:
        model = self.db.get(SampleModel, sample_id)
        return self._to_entity(model) if model else None

    def get_by_code(self, sample_code: str) -> Sample | None:
        model = self.db.query(SampleModel).filter(SampleModel.sample_code == sample_code).first()
        return self._to_entity(model) if model else None

    def get_by_client(self, client_id: int) -> list[Sample]:
        models = (
            self.db.query(SampleModel)
            .filter(SampleModel.client_id == client_id)
            .order_by(SampleModel.id)
            .all()
        )
        return [self._to_entity(m) for m in models]

    def get_all(self) -> list[Sample]:
        return [
            self._to_entity(m) for m in self.db.query(SampleModel).order_by(SampleModel.id).all()
        ]

    def update(self, sample: Sample) -> Sample:
        model = self.db.get(SampleModel, sample.id)
        if model is None:
            raise ValueError(f"Muestra {sample.id} no encontrada")
        model.sample_code = sample.sample_code
        model.sample_type = sample.sample_type
        model.description = sample.description
        model.client_id = sample.client_id
        model.received_date = sample.received_date
        self.db.flush()
        return sample


# ---------------------------------------------------------------------------
# Solicitudes
# ---------------------------------------------------------------------------


class SQLAlchemyRequestRepository(_BaseRepository, RequestRepository):
    """Repositorio de solicitudes sobre SQLAlchemy."""

    @staticmethod
    def _to_entity(model: RequestModel) -> Request:
        """Convierte una fila de `requests` en la entidad `Request`."""
        return Request(
            id=model.id,
            request_code=model.request_code,
            client_id=model.client_id,
            sample_id=model.sample_id,
            test_type=model.test_type,
            status=model.status,
            assigned_analyst_id=model.assigned_analyst_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def save(self, request: Request) -> Request:
        model = RequestModel(
            request_code=request.request_code,
            client_id=request.client_id,
            sample_id=request.sample_id,
            test_type=request.test_type,
            status=request.status,
            assigned_analyst_id=request.assigned_analyst_id,
            created_at=request.created_at,
            updated_at=request.updated_at,
        )
        self.db.add(model)
        self.db.flush()
        request.id = model.id
        return request

    def get_by_id(self, request_id: int) -> Request | None:
        model = self.db.get(RequestModel, request_id)
        return self._to_entity(model) if model else None

    def get_by_client(self, client_id: int) -> list[Request]:
        models = (
            self.db.query(RequestModel)
            .filter(RequestModel.client_id == client_id)
            .order_by(RequestModel.id.desc())
            .all()
        )
        return [self._to_entity(m) for m in models]

    def get_by_analyst(self, analyst_id: int) -> list[Request]:
        models = (
            self.db.query(RequestModel)
            .filter(RequestModel.assigned_analyst_id == analyst_id)
            .order_by(RequestModel.id.desc())
            .all()
        )
        return [self._to_entity(m) for m in models]

    def get_by_status(self, status: RequestStatus) -> list[Request]:
        models = (
            self.db.query(RequestModel)
            .filter(RequestModel.status == status)
            .order_by(RequestModel.id.desc())
            .all()
        )
        return [self._to_entity(m) for m in models]

    def get_all(self) -> list[Request]:
        models = self.db.query(RequestModel).order_by(RequestModel.id.desc()).all()
        return [self._to_entity(m) for m in models]

    def update(self, request: Request) -> Request:
        model = self.db.get(RequestModel, request.id)
        if model is None:
            raise ValueError(f"Solicitud {request.id} no encontrada")
        model.test_type = request.test_type
        model.status = request.status
        model.assigned_analyst_id = request.assigned_analyst_id
        model.updated_at = request.updated_at
        self.db.flush()
        return request


# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------


class SQLAlchemyResultRepository(_BaseRepository, ResultRepository):
    """Repositorio de resultados sobre SQLAlchemy."""

    @staticmethod
    def _to_entity(model: ResultModel) -> Result:
        """Convierte una fila de `results` en la entidad `Result`."""
        return Result(
            id=model.id,
            request_id=model.request_id,
            analyst_id=model.analyst_id,
            result_value=model.result_value,
            result_notes=model.result_notes,
            created_at=model.created_at,
        )

    def save(self, result: Result) -> Result:
        model = ResultModel(
            request_id=result.request_id,
            analyst_id=result.analyst_id,
            result_value=result.result_value,
            result_notes=result.result_notes,
            created_at=result.created_at,
        )
        self.db.add(model)
        self.db.flush()
        result.id = model.id
        return result

    def get_by_id(self, result_id: int) -> Result | None:
        model = self.db.get(ResultModel, result_id)
        return self._to_entity(model) if model else None

    def get_by_request(self, request_id: int) -> Result | None:
        model = self.db.query(ResultModel).filter(ResultModel.request_id == request_id).first()
        return self._to_entity(model) if model else None

    def get_all(self) -> list[Result]:
        models = self.db.query(ResultModel).order_by(ResultModel.id.desc()).all()
        return [self._to_entity(m) for m in models]

    def update(self, result: Result) -> Result:
        model = self.db.get(ResultModel, result.id)
        if model is None:
            raise ValueError(f"Resultado {result.id} no encontrado")
        model.result_value = result.result_value
        model.result_notes = result.result_notes
        self.db.flush()
        return result


# ---------------------------------------------------------------------------
# Notificaciones
# ---------------------------------------------------------------------------


class SQLAlchemyNotificationRepository(_BaseRepository, NotificationRepository):
    """Repositorio de notificaciones sobre SQLAlchemy."""

    @staticmethod
    def _to_entity(model: NotificationModel) -> Notification:
        """Convierte una fila de `notifications` en la entidad `Notification`."""
        return Notification(
            id=model.id,
            user_id=model.user_id,
            request_id=model.request_id,
            message=model.message,
            is_read=model.is_read,
            created_at=model.created_at,
        )

    def save(self, notification: Notification) -> Notification:
        model = NotificationModel(
            user_id=notification.user_id,
            request_id=notification.request_id,
            message=notification.message,
            is_read=notification.is_read,
            created_at=notification.created_at,
        )
        self.db.add(model)
        self.db.flush()
        notification.id = model.id
        return notification

    def get_by_id(self, notification_id: int) -> Notification | None:
        model = self.db.get(NotificationModel, notification_id)
        return self._to_entity(model) if model else None

    def get_by_user(self, user_id: int) -> list[Notification]:
        models = (
            self.db.query(NotificationModel)
            .filter(NotificationModel.user_id == user_id)
            .order_by(NotificationModel.id.desc())
            .all()
        )
        return [self._to_entity(m) for m in models]

    def mark_as_read(self, notification_id: int) -> Notification | None:
        model = self.db.get(NotificationModel, notification_id)
        if model is None:
            return None
        model.is_read = True
        self.db.flush()
        return self._to_entity(model)

    def get_all(self) -> list[Notification]:
        models = self.db.query(NotificationModel).order_by(NotificationModel.id.desc()).all()
        return [self._to_entity(m) for m in models]
