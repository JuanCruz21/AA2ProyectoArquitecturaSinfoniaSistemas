"""Configuracion comun de las pruebas.

Cada prueba se ejecuta contra una base de datos SQLite en memoria y limpia, de
forma que los tests son independientes entre si y no tocan `labcloud.db`.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.domain.entities import UserRole
from app.infrastructure.database import Base, get_db
from main import app

TEST_PASSWORD = "password123"


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Crea una base de datos en memoria nueva para cada prueba.

    `StaticPool` obliga a reutilizar la misma conexion; sin el, cada conexion
    abriria su propia base en memoria y las tablas pareceria que no existen.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Cliente HTTP de pruebas con la base de datos sustituida.

    Reproduce lo que hace `get_db()` en produccion: entrega la sesion y confirma
    la transaccion al terminar cada peticion.
    """
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Utilidades reutilizables
# ---------------------------------------------------------------------------


def create_user(client: TestClient, email: str, role: UserRole, name: str = "Usuario Prueba"):
    """Da de alta un usuario directamente en la base de datos de pruebas.

    Se usa el servicio y no la API porque crear roles privilegiados requiere ya
    estar autenticado como administrador, lo que complicaria el arranque.
    """
    from app.application.user_service import UserService
    from app.infrastructure.repositories import SQLAlchemyUserRepository

    # Se reutiliza el mismo override de sesion que usan las peticiones, para
    # que el usuario quede en la base de datos que vera el TestClient.
    session_generator = app.dependency_overrides[get_db]()
    db = next(session_generator)
    try:
        service = UserService(SQLAlchemyUserRepository(db))  # sin bus: no hace falta
        return service.create_user(
            email=email, password=TEST_PASSWORD, full_name=name, role=role
        )
    finally:
        next(session_generator, None)  # Cierra el generador y confirma la transaccion.


def login(client: TestClient, email: str, password: str = TEST_PASSWORD) -> dict[str, str]:
    """Inicia sesion y devuelve la cabecera `Authorization` lista para usar."""
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def admin_headers(client: TestClient) -> dict[str, str]:
    """Sesion iniciada como administrador."""
    create_user(client, "admin@test.com", UserRole.ADMIN, "Ana Admin")
    return login(client, "admin@test.com")


@pytest.fixture()
def receptionist_headers(client: TestClient) -> dict[str, str]:
    """Sesion iniciada como recepcionista."""
    create_user(client, "recepcion@test.com", UserRole.RECEPTIONIST, "Rita Recepcion")
    return login(client, "recepcion@test.com")


@pytest.fixture()
def analyst(client: TestClient):
    """Usuario analista dado de alta."""
    return create_user(client, "analista@test.com", UserRole.ANALYST, "Alba Analista")


@pytest.fixture()
def analyst_headers(client: TestClient, analyst) -> dict[str, str]:
    """Sesion iniciada como analista."""
    return login(client, "analista@test.com")


@pytest.fixture()
def client_user(client: TestClient):
    """Usuario con rol cliente."""
    return create_user(client, "cliente@test.com", UserRole.CLIENT, "Cesar Cliente")


@pytest.fixture()
def client_headers(client: TestClient, client_user) -> dict[str, str]:
    """Sesion iniciada como cliente."""
    return login(client, "cliente@test.com")
