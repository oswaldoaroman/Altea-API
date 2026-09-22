"""
Tests de los fallbacks sintéticos.
"""

import pytest

from service.conversation.fallbacks import (
    categoria_colesterol,
    categoria_glucosa,
    convertir_presion,
    parsear_categoria,
)


# ==========================================================
# CONVERTIR PRESIÓN
# ==========================================================

def test_convertir_presion_categoria_1():
    sistolica, diastolica = convertir_presion(1, 30, 76.0)
    # seed = 30 + 76 = 106
    # apHi = 110 + (106 % 20) = 110 + 6 = 116
    # apLo = 70 + (106 % 15) = 70 + 1 = 71
    assert sistolica == 116.0
    assert diastolica == 71.0


def test_convertir_presion_categoria_2():
    sistolica, diastolica = convertir_presion(2, 30, 76.0)
    # seed = 106
    # apHi = 130 + (106 % 10) = 130 + 6 = 136
    # apLo = 85 + (106 % 5) = 85 + 1 = 86
    assert sistolica == 136.0
    assert diastolica == 86.0


def test_convertir_presion_categoria_3():
    sistolica, diastolica = convertir_presion(3, 30, 76.0)
    # seed = 106
    # apHi = 140 + (106 % 20) = 140 + 6 = 146
    # apLo = 90 + (106 % 10) = 90 + 6 = 96
    assert sistolica == 146.0
    assert diastolica == 96.0


def test_convertir_presion_categoria_invalida():
    # Fallback por defecto.
    sistolica, diastolica = convertir_presion(99, 30, 76.0)
    assert sistolica == 120.0
    assert diastolica == 80.0


# ==========================================================
# CATEGORÍA GLUCOSA
# ==========================================================

@pytest.mark.parametrize(
    "mgdl, categoria",
    [
        (80.0, 1.0),
        (99.0, 1.0),
        (100.0, 2.0),
        (125.0, 2.0),
        (126.0, 3.0),
        (200.0, 3.0),
    ],
)
def test_categoria_glucosa(mgdl, categoria):
    assert categoria_glucosa(mgdl) == categoria


# ==========================================================
# CATEGORÍA COLESTEROL
# ==========================================================

@pytest.mark.parametrize(
    "mgdl, categoria",
    [
        (150.0, 1.0),
        (199.0, 1.0),
        (200.0, 2.0),
        (239.0, 2.0),
        (240.0, 3.0),
        (300.0, 3.0),
    ],
)
def test_categoria_colesterol(mgdl, categoria):
    assert categoria_colesterol(mgdl) == categoria


# ==========================================================
# PARSEAR CATEGORÍA — PRESIÓN
# ==========================================================

@pytest.mark.parametrize(
    "texto, categoria",
    [
        ("creo que es baja", 1),
        ("baja", 1),
        ("normal", 2),
        ("creo que es normal", 2),
        ("alta", 3),
        ("creo que es alta", 3),
        ("no sé", None),
        ("", None),
    ],
)
def test_parsear_categoria_presion(texto, categoria):
    assert parsear_categoria(texto, "presion") == categoria


# ==========================================================
# PARSEAR CATEGORÍA — GLUCOSA
# ==========================================================

@pytest.mark.parametrize(
    "texto, categoria",
    [
        ("normal", 1),
        ("creo que normal", 1),
        ("elevada", 2),
        ("creo que elevada", 2),
        ("alta", 3),
        ("muy alta", 3),
        ("no sé", None),
    ],
)
def test_parsear_categoria_glucosa(texto, categoria):
    assert parsear_categoria(texto, "glucosa") == categoria


# ==========================================================
# PARSEAR CATEGORÍA — COLESTEROL
# ==========================================================

@pytest.mark.parametrize(
    "texto, categoria",
    [
        ("normal", 1),
        ("elevado", 2),
        ("creo que elevado", 2),
        ("alto", 3),
        ("muy alto", 3),
        ("no sé", None),
    ],
)
def test_parsear_categoria_colesterol(texto, categoria):
    assert parsear_categoria(texto, "colesterol") == categoria


# ==========================================================
# CAMPO DESCONOCIDO
# ==========================================================

def test_parsear_categoria_campo_desconocido():
    assert parsear_categoria("normal", "campo_raro") is None