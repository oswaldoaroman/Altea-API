"""
Tests del extractor determinista de slots.

Los ejemplos están basados en los 40 casos reales que el usuario
proporcionó, más algunos casos borde.
"""

import pytest

from service.conversation.slots import extraer_slots


# ==========================================================
# HELPERS
# ==========================================================

def slots_a_dict(slots):
    return dict(slots)


# ==========================================================
# PESO
# ==========================================================

@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Peso 76 kilos", 76.0),
        ("Peso 76 kg", 76.0),
        ("Mi peso es de 76", 76.0),
        ("Peso 76", 76.0),
        ("peso: 76", 76.0),
    ],
)
def test_peso(texto, esperado):
    slots = slots_a_dict(extraer_slots(texto))
    assert slots.get("peso") == esperado


# ==========================================================
# ALTURA
# ==========================================================

@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Mido 1.75 metros", 175.0),
        ("Mido 175 cm", 175.0),
        ("Mi estatura es 1.75", 175.0),
        ("Tengo una altura de 175", 175.0),
        ("mido 1,75", 175.0),
        ("altura 180", 180.0),
    ],
)
def test_altura(texto, esperado):
    slots = slots_a_dict(extraer_slots(texto))
    assert slots.get("altura") == esperado


# ==========================================================
# PRESIÓN
# ==========================================================

@pytest.mark.parametrize(
    "texto",
    [
        "Mi presión es 130 sobre 85",
        "Tengo 130/85 de presión",
        "Mi presión arterial está en 130 sobre 85",
    ],
)
def test_presion_par(texto):
    slots = slots_a_dict(extraer_slots(texto))
    assert slots.get("presionSistolica") == 130.0
    assert slots.get("presionDiastolica") == 85.0


def test_presion_sistolica_diastolica_explicita():
    slots = slots_a_dict(
        extraer_slots("Tengo 130 de sistólica y 85 de diastólica")
    )
    assert slots.get("presionSistolica") == 130.0
    assert slots.get("presionDiastolica") == 85.0


# ==========================================================
# FUMA
# ==========================================================

@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Sí, fumo", True),
        ("No fumo", False),
        ("Soy fumador", True),
        ("Dejé de fumar", False),
        ("no soy fumador", False),
        ("nunca he fumado", False),
        ("fumo", True),
    ],
)
def test_fuma(texto, esperado):
    slots = slots_a_dict(extraer_slots(texto))
    assert slots.get("fuma") is esperado


# ==========================================================
# ALCOHOL
# ==========================================================

@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Sí, consumo alcohol", True),
        ("No tomo alcohol", False),
        ("Bebo alcohol ocasionalmente", True),
        ("No consumo bebidas alcohólicas", False),
        ("consumo alcohol", True),
        ("bebo ocasionalmente", True),
        ("nunca tomo", False),
    ],
)
def test_alcohol(texto, esperado):
    slots = slots_a_dict(extraer_slots(texto))
    assert slots.get("consumeAlcohol") is esperado


# ==========================================================
# ACTIVIDAD FÍSICA
# ==========================================================

@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Hago ejercicio regularmente", 0),
        ("No hago ejercicio", 2),
        ("Soy sedentario", 2),
        ("Hago actividad física", 1),
        ("Casi no hago ejercicio", 2),
        ("soy activo", 0),
        ("nada de ejercicio", 2),
    ],
)
def test_actividad(texto, esperado):
    slots = slots_a_dict(extraer_slots(texto))
    assert slots.get("actividadFisica") == esperado


# ==========================================================
# GLUCOSA
# ==========================================================

@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Mi glucosa es 100", 100.0),
        ("Tengo 100 de glucosa", 100.0),
        ("Mi azúcar está en 100", 100.0),
        ("Tengo la glucosa en 100 mg/dL", 100.0),
    ],
)
def test_glucosa(texto, esperado):
    slots = slots_a_dict(extraer_slots(texto))
    assert slots.get("glucosa") == esperado


# ==========================================================
# COLESTEROL
# ==========================================================

@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Mi colesterol es 200", 200.0),
        ("Tengo 200 de colesterol", 200.0),
        ("Mi colesterol está en 200 mg/dL", 200.0),
        ("Me salió el colesterol en 200", 200.0),
    ],
)
def test_colesterol(texto, esperado):
    slots = slots_a_dict(extraer_slots(texto))
    assert slots.get("colesterol") == esperado


# ==========================================================
# COMBINADAS
# ==========================================================

def test_combinada_peso_altura():
    slots = slots_a_dict(extraer_slots("Peso 76 kilos y mido 1.75"))
    assert slots.get("peso") == 76.0
    assert slots.get("altura") == 175.0


def test_combinada_presion_peso():
    slots = slots_a_dict(
        extraer_slots("Tengo 130 sobre 85 de presión y peso 76 kg")
    )
    assert slots.get("presionSistolica") == 130.0
    assert slots.get("presionDiastolica") == 85.0
    assert slots.get("peso") == 76.0


def test_combinada_habitos():
    slots = slots_a_dict(
        extraer_slots("No fumo, no tomo alcohol y hago ejercicio")
    )
    assert slots.get("fuma") is False
    assert slots.get("consumeAlcohol") is False
    assert slots.get("actividadFisica") == 1


def test_combinada_tres_numericos():
    slots = slots_a_dict(
        extraer_slots("Peso 80 kilos, mido 1.80 y mi presión es 120/80")
    )
    assert slots.get("peso") == 80.0
    assert slots.get("altura") == 180.0
    assert slots.get("presionSistolica") == 120.0
    assert slots.get("presionDiastolica") == 80.0


def test_combinada_glucosa_colesterol():
    slots = slots_a_dict(
        extraer_slots("Tengo glucosa de 100 y colesterol de 200")
    )
    assert slots.get("glucosa") == 100.0
    assert slots.get("colesterol") == 200.0


def test_combinada_habitos_mixtos():
    slots = slots_a_dict(
        extraer_slots("Soy sedentario, no fumo y tomo alcohol ocasionalmente")
    )
    assert slots.get("actividadFisica") == 2
    assert slots.get("fuma") is False
    assert slots.get("consumeAlcohol") is True


def test_combinada_completa():
    slots = slots_a_dict(
        extraer_slots(
            "Peso 76, mido 175 cm, tengo 130/85 de presión, "
            "no fumo y hago ejercicio"
        )
    )
    assert slots.get("peso") == 76.0
    assert slots.get("altura") == 175.0
    assert slots.get("presionSistolica") == 130.0
    assert slots.get("presionDiastolica") == 85.0
    assert slots.get("fuma") is False
    assert slots.get("actividadFisica") == 1


# ==========================================================
# CASOS BORDE
# ==========================================================

def test_texto_vacio():
    assert extraer_slots("") == []


def test_texto_sin_datos():
    assert extraer_slots("Hola Altea, ¿cómo estás?") == []


def test_peso_fuera_de_rango_no_se_extrae():
    # 500 kg es absurdo, no se extrae
    slots = slots_a_dict(extraer_slots("Peso 500 kg"))
    assert "peso" not in slots


def test_altura_fuera_de_rango_no_se_extrae():
    # 5 metros es absurdo, no se extrae
    slots = slots_a_dict(extraer_slots("Mido 5 metros"))
    assert "altura" not in slots


def test_presion_invertida_no_se_extrae():
    # Sistólica < diastólica no tiene sentido
    slots = slots_a_dict(extraer_slots("Tengo 80/120 de presión"))
    assert "presionSistolica" not in slots
    assert "presionDiastolica" not in slots


def test_peso_con_coma_decimal():
    slots = slots_a_dict(extraer_slots("peso 76,5"))
    assert slots.get("peso") == 76.5

# ==========================================================
# EDAD
# ==========================================================

@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Tengo 30 años", 30),
        ("30 años", 30),
        ("Mi edad es 45", 45),
        ("edad 50", 50),
        ("tengo 25 años", 25),
    ],
)
def test_edad(texto, esperado):
    slots = slots_a_dict(extraer_slots(texto))
    assert slots.get("edad") == esperado


def test_edad_fuera_de_rango_no_se_extrae():
    slots = slots_a_dict(extraer_slots("Tengo 200 años"))
    assert "edad" not in slots


def test_edad_decimal_no_se_extrae():
    slots = slots_a_dict(extraer_slots("Tengo 30.5 años"))
    assert "edad" not in slots