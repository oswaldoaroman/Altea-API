"""
Dependencias de FastAPI para autenticación.

`get_current_user` se usa como dependencia en cualquier endpoint
que requiera usuario autenticado.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database.connection import get_db
from models.usuarios import Usuario

from .jwt import decodificar_token


# Esquema HTTP Bearer: espera header `Authorization: Bearer <token>`.
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    Obtiene el usuario autenticado a partir del token JWT.

    Lanza 401 si:
    - No hay token.
    - El token es inválido o expirado.
    - El usuario del token no existe en la BD.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el token de autenticación.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decodificar_token(credentials.credentials)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario = (
        db.query(Usuario)
        .filter(Usuario.id_usuario == user_id)
        .first()
    )

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return usuario