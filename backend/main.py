"""LabCloud - Punto de entrada de la API.

Este modulo cumple el papel de API Gateway del sistema: es la unica puerta de
entrada, centraliza CORS, agrupa los routers de los seis servicios y traduce
los errores del dominio a respuestas HTTP.

Arranque:
    uv run uvicorn main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.domain.entities import DomainError
from app.infrastructure.database import init_db
from app.presentation import (
    auth_routes,
    client_routes,
    notification_routes,
    request_routes,
    result_routes,
    sample_routes,
    user_routes,
)

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("labcloud")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Prepara y libera los recursos de la aplicacion.

    Al arrancar se crea el esquema de la base de datos. Hacerlo aqui, y no al
    importar los modulos, evita efectos secundarios inesperados al ejecutar las
    pruebas o los scripts auxiliares. El bus de eventos, en cambio, se construye
    una vez por peticion (ver `app/presentation/dependencies.py`).
    """
    init_db()
    logger.info("%s iniciada (debug=%s)", settings.app_name, settings.debug)
    yield
    logger.info("%s detenida", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description=(
        "API REST para la gestion de analisis de laboratorio.\n\n"
        "Arquitectura por capas (presentacion, aplicacion, dominio e "
        "infraestructura) organizada en seis servicios: usuarios, clientes, "
        "muestras, solicitudes, resultados y notificaciones.\n\n"
        "**Como probar la API desde aqui**: llame primero a "
        "`POST /api/auth/login`, copie el `access_token` de la respuesta y "
        "peguelo en el boton *Authorize*."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: solo se permiten los origenes declarados en la configuracion, que en
# desarrollo es el servidor de Next.js.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    """Traduce las violaciones de reglas de negocio a HTTP 400.

    Gracias a este manejador, los servicios y el dominio pueden lanzar
    `DomainError` sin conocer nada de HTTP, y las rutas quedan libres de
    bloques `try/except` repetidos.
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


# Registro de los routers de cada servicio (patron API Gateway).
app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(client_routes.router)
app.include_router(sample_routes.router)
app.include_router(request_routes.router)
app.include_router(result_routes.router)
app.include_router(notification_routes.router)


@app.get("/", tags=["Sistema"], summary="Informacion de la API")
def root() -> dict:
    """Devuelve los datos basicos de la API y donde esta su documentacion."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


@app.get("/health", tags=["Sistema"], summary="Comprobacion de estado")
def health_check() -> dict:
    """Indica si el servicio esta operativo. Lo usan los balanceadores."""
    return {"status": "healthy"}


if __name__ == "__main__":
    # Permite ejecutar `python main.py` ademas de `uvicorn main:app`.
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.debug,
        # Sin esto, el recargador vigila tambien `.venv`. Al instalar o
        # actualizar dependencias con el servidor en marcha, cada archivo
        # escrito ahi dispara una recarga y la consola se llena de avisos.
        reload_excludes=[".venv/*", "*.db"],
    )
