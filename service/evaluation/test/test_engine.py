"""
Tests del motor de evaluación.

Carga cases.json y verifica que el motor produce el score esperado.

Los expected_score deben ser generados por el motor Dart actual
para garantizar consistencia entre motores.
"""

import json
from pathlib import Path

import pytest

from service.evaluation.engine import evaluar
from service.evaluation.models import EvaluationInput


CASES_PATH = Path(__file__).parent / "cases.json"


def cargar_casos():
    with open(CASES_PATH, encoding="utf-8") as f:
        return json.load(f)


CASES = cargar_casos()


@pytest.mark.parametrize(
    "case",
    CASES,
    ids=[c["name"] for c in CASES],
)
def test_engine_matches_expected(case):
    """
    Verifica que el motor devuelve el score esperado.
    """

    expected = case["expected_score"]

    if expected is None:
        pytest.skip(
            "Caso sin expected_score. "
            "Ejecutar el motor Dart para generarlo."
        )

    input = EvaluationInput.from_dict(case["input"])

    result = evaluar(input, age=case["age"])

    assert result.score == pytest.approx(expected, abs=1e-6), (
        f"Score inesperado para '{case['name']}': "
        f"esperado {expected}, obtenido {result.score}"
    )


def test_nivel_se_deriva_del_score():
    """
    Verifica que el nivel se deriva correctamente.
    """

    input = EvaluationInput(
        ap_hi=110.0, ap_lo=70.0,
        weight=60.0, height=165.0,
        cholesterol=1.0, gluc=1.0,
        smoke=0.0, alco=0.0, active=1.0,
    )

    result = evaluar(input, age=25.0)

    assert result.level in {"bajo", "moderado", "alto", "muy_alto"}


def test_score_siempre_positivo():
    """
    Sanity check: el motor nunca devuelve negativos.
    """

    input = EvaluationInput(
        ap_hi=200.0, ap_lo=110.0,
        weight=150.0, height=150.0,
        cholesterol=3.0, gluc=3.0,
        smoke=1.0, alco=1.0, active=0.0,
    )

    result = evaluar(input, age=80.0)

    assert result.score > 0