"""
Tests de creación y verificación de JWT.
"""

import time

from service.security.jwt import crear_token, decodificar_token


def test_crear_y_decodificar():
    token = crear_token(user_id=42)
    user_id = decodificar_token(token)

    assert user_id == 42


def test_token_invalido():
    assert decodificar_token("esto.no.es.un.jwt") is None


def test_token_vacio():
    assert decodificar_token("") is None


def test_token_manipulado():
    token = crear_token(user_id=1)
    # Cambiar un carácter al final invalida la firma.
    manipulado = token[:-1] + ("A" if token[-1] != "A" else "B")

    assert decodificar_token(manipulado) is None


def test_distintos_user_ids():
    for uid in [1, 100, 99999]:
        token = crear_token(user_id=uid)
        assert decodificar_token(token) == uid