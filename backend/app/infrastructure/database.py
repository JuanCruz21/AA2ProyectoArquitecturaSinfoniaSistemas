"""Configuracion de la base de datos y modelos ORM.

Aqui viven los detalles tecnicos de persistencia: el motor de SQLite, la
fabrica de sesiones y las tablas de SQLAlchemy. Los modelos ORM de este modulo
son *distintos* de las entidades del dominio a proposito: asi el dominio no
queda atado al ORM y se pueden evolucionar por separado.
"""

from collections.abc import Generator
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings
from app.domain.entities import RequestStatus, UserRole


def _utcnow() -> datetime:
    """Valor por defecto de las columnas de fecha, siempre en UTC."""
    return datetime.now(timezone.utc)


# `check_same_thread=False` es necesario porque uvicorn atiende las peticiones
# en varios hilos y, por defecto, SQLite prohibe compartir una conexion entre
# ellos. Solo aplica a SQLite; con PostgreSQL este argumento sobra.
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=_connect_args, future=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

Base = declarative_base()


# ---------------------------------------------------------------------------
# Modelos ORM (tablas)
# ---------------------------------------------------------------------------


class UserModel(Base):
    """Tabla `users`."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CLIENT, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)


class ClientModel(Base):
    """Tabla `clients`."""

    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(50), default="", nullable=False)
    address = Column(String(500), default="", nullable=False)
    # Cuenta de acceso asociada, para que el cliente consulte solo lo suyo.
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)


class SampleModel(Base):
    """Tabla `samples`."""

    __tablename__ = "samples"

    id = Column(Integer, primary_key=True, index=True)
    sample_code = Column(String(50), unique=True, index=True, nullable=False)
    sample_type = Column(String(100), nullable=False)
    description = Column(String(500), default="", nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True, nullable=False)
    received_date = Column(DateTime, default=_utcnow, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)


class RequestModel(Base):
    """Tabla `requests`."""

    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    request_code = Column(String(50), unique=True, index=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True, nullable=False)
    sample_id = Column(Integer, ForeignKey("samples.id"), index=True, nullable=False)
    test_type = Column(String(255), nullable=False)
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False, index=True)
    assigned_analyst_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)


class ResultModel(Base):
    """Tabla `results`.

    `request_id` es unico: una solicitud tiene como mucho un resultado. La regla
    tambien se valida en el servicio, pero se refuerza en la base de datos.
    """

    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), unique=True, index=True, nullable=False)
    analyst_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    result_value = Column(String(2000), nullable=False)
    result_notes = Column(String(2000), default="", nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)


class NotificationModel(Base):
    """Tabla `notifications`."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    request_id = Column(Integer, ForeignKey("requests.id"), index=True, nullable=False)
    message = Column(String(500), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)


# ---------------------------------------------------------------------------
# Sesiones y creacion del esquema
# ---------------------------------------------------------------------------


def init_db() -> None:
    """Crea las tablas que aun no existan.

    Se invoca explicitamente al arrancar la aplicacion (ver `main.py`) y desde
    `init_db.py`. No se ejecuta al importar el modulo: un import no debe tener
    efectos secundarios sobre la base de datos.
    """
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependencia de FastAPI que entrega una sesion por peticion.

    Implementa el patron Unit of Work: la transaccion se confirma una sola vez
    al terminar la peticion con exito y se deshace entera si algo falla. Por eso
    los repositorios usan `flush()` en lugar de `commit()`; asi una operacion
    compuesta (por ejemplo registrar un resultado y cerrar la solicitud) no
    puede quedar a medias.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
