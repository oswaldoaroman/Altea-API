"""
Hashing y verificación de contraseñas.

Usa `bcrypt` directamente (sin passlib).

NOTA HISTÓRICA:
Usábamos `passlib`, pero tiene un bug conocido con `bcrypt` 4.1+
(ValueError: password cannot be longer than 72 bytes).
Desde 2024, la comunidad recomienda usar `bcrypt` directamente.
"""

from __future__ import annotations

import bcrypt


# bcrypt tiene un límite de 72 bytes. La documentación oficial
# recomienda truncar los passwords antes de hashearlos.
_BCRYPT_MAX_BYTES = 72


def _normalizar_password(password: str) -> bytes:
    """
    Convierte el password a bytes y lo trunca a 72 bytes.

    El truncado es la práctica recomendada por la propia librería
    `bcrypt` (así lo hace también Django, Flask-Security, etc.).
    """
    if not password:
        raise ValueError("La contraseña no puede estar vacía.")

    encoded = password.encode("utf-8")

    # Truncar a 72 bytes.
    return encoded[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """
    Genera el hash bcrypt de una contraseña en texto plano.

    Devuelve un string (con salt incluido y prefijo $2b$).
    """
    password_bytes = _normalizar_password(password)

    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)

    return hashed.decode("utf-8")


def verificar_password(password: str, password_hash: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con su hash.

    Devuelve True si coinciden, False si no.
    """
    if not password or not password_hash:
        return False

    try:
        password_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        hash_bytes = password_hash.encode("utf-8")

        return bcrypt.checkpw(password_bytes, hash_bytes)

    except Exception:
        # Si el hash está mal formado, no lanzamos. Devolvemos False.
        return False