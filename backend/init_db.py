"""Carga la base de datos con datos de prueba.

Crea las tablas si no existen y da de alta un usuario por cada rol, dos
clientes del laboratorio (enlazados a sus cuentas de acceso), varias muestras y
una solicitud de ejemplo. El script es idempotente: se puede volver a ejecutar
sin duplicar informacion.

Uso:
    uv run python init_db.py
"""

import logging

from app.application.client_service import ClientService
from app.application.event_handlers import build_event_bus
from app.application.request_service import RequestService
from app.application.sample_service import SampleService
from app.application.user_service import UserService
from app.domain.entities import Client, DomainError, User, UserRole
from app.infrastructure.database import get_db, init_db
from app.infrastructure.repositories import (
    SQLAlchemyClientRepository,
    SQLAlchemyRequestRepository,
    SQLAlchemySampleRepository,
    SQLAlchemyUserRepository,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("seed")

# Contrasena comun de todas las cuentas de demostracion. Solo para desarrollo.
DEMO_PASSWORD = "password123"

# Usuarios de demostracion: (email, nombre, rol)
DEMO_USERS = [
    ("admin@labcloud.com", "Ana Administradora", UserRole.ADMIN),
    ("recepcion@labcloud.com", "Ricardo Recepcion", UserRole.RECEPTIONIST),
    ("analista@labcloud.com", "Alicia Analista", UserRole.ANALYST),
    ("cliente@labcloud.com", "Carlos Cliente", UserRole.CLIENT),
]


def _ensure_user(service: UserService, email: str, name: str, role: UserRole) -> User:
    """Crea el usuario si no existe y lo devuelve en cualquier caso."""
    existing = service.repository.get_by_email(email)
    if existing:
        logger.info("  = Usuario ya existente: %s", email)
        return existing

    user = service.create_user(
        email=email, password=DEMO_PASSWORD, full_name=name, role=role
    )
    logger.info("  + Usuario creado: %-26s (%s)", email, role.value)
    return user


def _ensure_client(
    service: ClientService,
    name: str,
    email: str,
    phone: str,
    address: str,
    user_id: int | None = None,
) -> Client:
    """Crea el cliente si no existe y lo devuelve en cualquier caso."""
    existing = service.repository.get_by_email(email)
    if existing:
        logger.info("  = Cliente ya existente: %s", name)
        return existing

    client = service.create_client(
        name=name, email=email, phone=phone, address=address, user_id=user_id
    )
    logger.info("  + Cliente creado: %s", name)
    return client


def seed() -> None:
    """Puebla la base de datos con el juego de datos de demostracion."""
    init_db()

    # Se reutiliza la dependencia `get_db()` para trabajar igual que una
    # peticion HTTP: toda la carga ocurre dentro de una unica transaccion.
    db_context = get_db()
    db = next(db_context)
    # Bus con los suscriptores de notificaciones enlazados a esta sesion.
    bus = build_event_bus(db)

    try:
        logger.info("\nUsuarios")
        user_service = UserService(SQLAlchemyUserRepository(db), bus)
        usuarios = {
            role: _ensure_user(user_service, email, name, role)
            for email, name, role in DEMO_USERS
        }

        logger.info("\nClientes del laboratorio")
        client_service = ClientService(SQLAlchemyClientRepository(db), bus)
        clinica = _ensure_client(
            client_service,
            name="Clinica San Jose",
            email="contacto@clinicasanjose.com",
            phone="+57 601 1234567",
            address="Calle 10 #5-50, Bogota",
            # Se enlaza con la cuenta de Carlos para que pueda ver sus resultados.
            user_id=usuarios[UserRole.CLIENT].id,
        )
        hospital = _ensure_client(
            client_service,
            name="Hospital Central",
            email="info@hospitalcentral.com",
            phone="+57 601 9876543",
            address="Carrera 7 #20-30, Bogota",
        )

        logger.info("\nMuestras")
        sample_repo = SQLAlchemySampleRepository(db)
        sample_service = SampleService(sample_repo, SQLAlchemyClientRepository(db))
        muestras = []
        for tipo, descripcion, cliente in [
            ("Sangre", "Hemograma completo", clinica),
            ("Orina", "Uroanalisis completo", clinica),
            ("Sangre", "Perfil lipidico", hospital),
        ]:
            muestra = sample_service.create_sample(
                sample_type=tipo, description=descripcion, client_id=cliente.id
            )
            muestras.append(muestra)
            logger.info("  + Muestra creada: %s (%s)", muestra.sample_code, tipo)

        logger.info("\nSolicitudes")
        request_service = RequestService(
            SQLAlchemyRequestRepository(db),
            SQLAlchemyClientRepository(db),
            sample_repo,
            SQLAlchemyUserRepository(db),
            bus,
        )
        solicitud = request_service.create_request(
            client_id=clinica.id,
            sample_id=muestras[0].id,
            test_type="Hemograma completo",
        )
        logger.info("  + Solicitud creada: %s", solicitud.request_code)

        # Se deja asignada y en analisis para poder probar el registro de
        # resultados nada mas arrancar.
        request_service.assign_analyst(solicitud.id, usuarios[UserRole.ANALYST].id)
        request_service.start_analysis(solicitud.id)
        logger.info("  > Asignada a %s y puesta en analisis", usuarios[UserRole.ANALYST].email)

        # Cierra el generador, lo que dispara el commit de la transaccion.
        next(db_context, None)

    except DomainError as exc:
        logger.error("\nNo se pudo completar la carga: %s", exc)
        db_context.close()
        raise
    except Exception:
        db_context.close()
        raise

    logger.info("\n%s", "-" * 58)
    logger.info("Base de datos lista. Cuentas de prueba (contrasena: %s)", DEMO_PASSWORD)
    logger.info("%s", "-" * 58)
    for email, _, role in DEMO_USERS:
        logger.info("  %-11s %s", role.value + ":", email)
    logger.info("%s\n", "-" * 58)


if __name__ == "__main__":
    seed()
