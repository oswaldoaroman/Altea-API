"""
Router de usuarios: registro, login y datos públicos.

Los endpoints GET se mantienen para debug. En producción se
podrían proteger con autenticación de administrador.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.connection import get_db
from models.usuarios import Usuario
from schemas.usuarios import (
    TokenResponse,
    UsuarioLogin,
    UsuarioRegistro,
    UsuarioResponse,
)
from service.security.dependencies import get_current_user
from service.security.jwt import crear_token
from service.security.password import hash_password, verificar_password


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
)


# ==========================================================
# REGISTRO
# ==========================================================

@router.post(
    "/registro",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def registrar_usuario(
    datos: UsuarioRegistro,
    db: Session = Depends(get_db),
):
    """
    Registra un usuario nuevo y devuelve un token JWT.

    Errores:
    - 409 si el correo ya está registrado.
    """

    existente = (
        db.query(Usuario)
        .filter(Usuario.correo == datos.correo)
        .first()
    )

    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese correo.",
        )

    usuario = Usuario(
        nombre=datos.nombre,
        correo=datos.correo,
        password_hash=hash_password(datos.password),
        fecha_nacimiento=datos.fecha_nacimiento,
        genero=datos.genero.value,
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    token = crear_token(usuario.id_usuario)

    return TokenResponse(
        access_token=token,
        usuario=UsuarioResponse.model_validate(usuario),
    )


# ==========================================================
# LOGIN
# ==========================================================

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login_usuario(
    datos: UsuarioLogin,
    db: Session = Depends(get_db),
):
    """
    Inicia sesión con correo y contraseña.

    Errores:
    - 401 si las credenciales son incorrectas.
    """

    usuario = (
        db.query(Usuario)
        .filter(Usuario.correo == datos.correo)
        .first()
    )

    if usuario is None or not verificar_password(
        datos.password,
        usuario.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
        )

    token = crear_token(usuario.id_usuario)

    return TokenResponse(
        access_token=token,
        usuario=UsuarioResponse.model_validate(usuario),
    )


# ==========================================================
# USUARIO AUTENTICADO
# ==========================================================

@router.get(
    "/me",
    response_model=UsuarioResponse,
)
def obtener_usuario_actual(
    usuario: Usuario = Depends(get_current_user),
):
    """
    Devuelve los datos del usuario autenticado.

    Requiere header: Authorization: Bearer <token>
    """
    return usuario


# ==========================================================
# ENDPOINTS PÚBLICOS (debug)
# ==========================================================

@router.get("/", response_model=list[UsuarioResponse])
def obtener_usuarios(db: Session = Depends(get_db)):
    return db.query(Usuario).all()


@router.get("/{id_usuario}", response_model=UsuarioResponse)
def obtener_usuario(id_usuario: int, db: Session = Depends(get_db)):
    usuario = (
        db.query(Usuario)
        .filter(Usuario.id_usuario == id_usuario)
        .first()
    )

    if usuario is None:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado",
        )

    return usuario


@router.delete("/{id_usuario}")
def eliminar_usuario(id_usuario: int, db: Session = Depends(get_db)):
    usuario = (
        db.query(Usuario)
        .filter(Usuario.id_usuario == id_usuario)
        .first()
    )

    if usuario is None:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado",
        )

    db.delete(usuario)
    db.commit()

    return {"mensaje": "Usuario eliminado"}