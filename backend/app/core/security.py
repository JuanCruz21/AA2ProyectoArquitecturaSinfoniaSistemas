"""Utilidades de seguridad: hash de contrasenas y JSON Web Tokens.

Se usa la libreria `bcrypt` directamente en lugar de `passlib`, porque passlib
1.7.4 esta sin mantenimiento y es incompatible con bcrypt >= 4.1 (falla al leer
`bcrypt.__about__`). Trabajar con bcrypt de forma directa evita ese conflicto y
mantiene el codigo igual de corto.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# bcrypt solo considera los primeros 72 bytes de la contrasena y, desde la
# version 4.x, lanza un error si recibe mas. Se trunca de forma explicita para
# que el comportamiento sea predecible.
BCRYPT_MAX_BYTES = 72


class TokenError(Exception):
    """Error al validar un token JWT (expirado, manipulado o mal formado)."""


def _encode(password: str) -> bytes:
    """Convierte la contrasena a bytes respetando el limite de bcrypt."""
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de una contrasena en claro.

    El `salt` se genera aleatoriamente en cada llamada, por lo que dos usuarios
    con la misma contrasena tendran hashes distintos.
    """
    return bcrypt.hashpw(_encode(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Comprueba una contrasena en claro contra su hash almacenado."""
    try:
        return bcrypt.checkpw(_encode(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        # Hash corrupto o con formato desconocido: se trata como no valido.
        return False


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Genera un JWT firmado con los datos indicados.

    Args:
        data: Claims a incluir (por ejemplo `sub`, `user_id` y `role`).
        expires_delta: Vigencia del token. Si se omite se usa la configurada.

    Returns:
        El token codificado como cadena.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    # `exp` e `iat` son claims estandar; PyJWT valida `exp` automaticamente.
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Verifica la firma y la vigencia de un token y devuelve sus claims.

    Raises:
        TokenError: Si el token expiro o no es valido.
    """
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("El token ha expirado") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Token invalido") from exc
