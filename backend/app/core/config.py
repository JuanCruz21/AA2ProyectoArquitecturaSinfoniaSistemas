"""Configuracion centralizada de la aplicacion.

Todos los parametros se leen del archivo `.env` (o de variables de entorno) para
no dejar valores sensibles escritos en el codigo. Es la unica pieza que conoce
el entorno de ejecucion: el resto de capas depende de este objeto `settings`.
"""

import json
import logging
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

logger = logging.getLogger(__name__)

# Valor por defecto de la clave de firma. Sirve para que el proyecto arranque
# sin configuracion, pero NO debe usarse fuera de desarrollo.
INSECURE_DEFAULT_SECRET = "clave-de-desarrollo-no-usar-en-produccion"


class Settings(BaseSettings):
    """Parametros de configuracion de LabCloud."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Aplicacion -------------------------------------------------------
    app_name: str = "LabCloud API"
    debug: bool = True

    # --- Base de datos ----------------------------------------------------
    # SQLite es suficiente para el prototipo. Cambiar esta URL por una de
    # PostgreSQL basta para migrar, porque el acceso a datos esta aislado
    # detras del patron Repository.
    database_url: str = "sqlite:///./labcloud.db"

    # --- Seguridad --------------------------------------------------------
    secret_key: str = INSECURE_DEFAULT_SECRET
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    # Longitud minima exigida a las contrasenas al registrar un usuario.
    min_password_length: int = 8

    # --- CORS -------------------------------------------------------------
    # Origenes autorizados a consumir la API desde el navegador. Se incluyen
    # las dos formas de escribir la direccion local: el navegador las considera
    # origenes distintos, y abrir la aplicacion por 127.0.0.1 con solo
    # `localhost` autorizado provoca un error de CORS dificil de diagnosticar.
    #
    # `NoDecode` es imprescindible: sin el, pydantic-settings intenta
    # interpretar la variable de entorno como JSON *antes* de llamar al
    # validador, y un valor separado por comas aborta el arranque con
    # "error parsing value for field cors_origins". Con `NoDecode` el texto
    # llega intacto y lo interpreta el validador de abajo.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Acepta CORS_ORIGINS como JSON o como lista separada por comas.

        Ambas formas son validas en el `.env`:
            CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
            CORS_ORIGINS='["http://localhost:3000"]'
        """
        if not isinstance(value, str):
            return value

        texto = value.strip()
        if texto.startswith("["):
            return json.loads(texto)
        return [origin.strip() for origin in texto.split(",") if origin.strip()]

    @property
    def uses_insecure_secret(self) -> bool:
        """Indica si se esta usando la clave de firma por defecto."""
        return self.secret_key == INSECURE_DEFAULT_SECRET


# Instancia unica compartida por toda la aplicacion (patron Singleton simple).
settings = Settings()

if settings.uses_insecure_secret:
    logger.warning(
        "Se esta usando SECRET_KEY por defecto. Defina una propia en backend/.env "
        "antes de desplegar la aplicacion."
    )
