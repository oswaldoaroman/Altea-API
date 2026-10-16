"""
Creación y verificación de tokens JWT.

Usa python-jose. Los tokens tienen expiración configurable y
contienen el `user_id` del usuario autenticado.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from database.jwt_config import (
    JWT_ALGORITHM,
    JWT_EXPIRES_DAYS,
    JWT_SECRET_KEY,
)


def crear_token(user_id: int) -> str:
    """
    Crea un JWT firmado que identifica al usuario.

    El token incluye:
    - `sub`: el user_id (como string).
    - `exp`: fecha de expiración.
    - `iat`: fecha de emisión.
    """

    ahora = datetime.now(timezone.utc)
    expira = ahora + timedelta(days=JWT_EXPIRES_DAYS)

    payload = {
        "sub": str(user_id),
        "iat": int(ahora.timestamp()),
        "exp": int(expira.timestamp()),
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def decodificar_token(token: str) -> int | None:
    """
    Verifica y decodifica un JWT.

    Devuelve el `user_id` si es válido, o `None` si no.
    """

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        sub = payload.get("sub")

        if sub is None:
            return None

        return int(sub)

    except (JWTError, ValueError):
        return None