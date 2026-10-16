"""
Tests de hashing y verificación de contraseñas.
"""

import pytest

from service.security.password import hash_password, verificar_password


def test_hash_y_verificar():
    password = "mi_contraseña_segura_123"
    hash_generado = hash_password(password)

    # El hash NO debe ser igual a la contraseña.
    assert hash_generado != password

    # La verificación debe funcionar.
    assert verificar_password(password, hash_generado) is True


def test_password_incorrecta():
    hash_generado = hash_password("correcta")

    assert verificar_password("incorrecta", hash_generado) is False


def test_hash_vacio():
    with pytest.raises(ValueError):
        hash_password("")


def test_verificar_password_vacia():
    hash_generado = hash_password("correcta")

    assert verificar_password("", hash_generado) is False


def test_verificar_hash_vacio():
    assert verificar_password("algo", "") is False


def test_verificar_hash_malformado():
    # No debe explotar aunque el hash sea basura.
    assert verificar_password("algo", "no-es-un-hash-valido") is False


def test_hashes_diferentes_para_misma_password():
    """Bcrypt usa salt, así que dos hashes del mismo texto son distintos."""

    h1 = hash_password("misma")
    h2 = hash_password("misma")

    assert h1 != h2
    assert verificar_password("misma", h1) is True
    assert verificar_password("misma", h2) is True