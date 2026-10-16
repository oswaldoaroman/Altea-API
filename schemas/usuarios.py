"""
Schemas Pydantic para usuarios y autenticación.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ==========================================================
# ENUMS
# ==========================================================

class GeneroEnum(str, Enum):
    MASCULINO = "Masculino"
    FEMENINO = "Femenino"


# ==========================================================
# ENTRADA
# ==========================================================

class UsuarioRegistro(BaseModel):
    """
    Payload del endpoint POST /usuarios/registro.
    """

    nombre: str = Field(..., min_length=1, max_length=100)
    correo: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    fecha_nacimiento: date
    genero: GeneroEnum


class UsuarioLogin(BaseModel):
    """
    Payload del endpoint POST /usuarios/login.
    """

    correo: EmailStr
    password: str


# ==========================================================
# SALIDA
# ==========================================================

class UsuarioResponse(BaseModel):
    """
    Datos públicos del usuario. NUNCA incluye password_hash.
    """

    id_usuario: int
    nombre: str
    correo: EmailStr
    fecha_nacimiento: date
    genero: str
    fecha_registro: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """
    Respuesta al registrar o iniciar sesión.
    """

    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse