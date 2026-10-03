"""
Motor determinista de evaluación de riesgo cardiovascular.

Port literal del motor Dart (EvaluacionService.evaluar).
Los umbrales, comparaciones y estructura deben ser idénticos
al motor Dart para garantizar consistencia entre flujos
(offline formulario / online chatbot).

NO modificar sin actualizar también el motor Dart
y los casos de prueba en tests/cases.json.
"""

from __future__ import annotations

from .levels import nivel_desde_score
from .models import EvaluationInput, EvaluationResult


# ==========================================================
# MOTOR
# ==========================================================

def evaluar(input: EvaluationInput, age: float) -> EvaluationResult:
    """
    Evalúa el riesgo cardiovascular.

    `input` contiene los datos del usuario (sin edad).
    `age` es la edad en años, parámetro aparte.
    """

    score = _score(input, age)

    return EvaluationResult(
        score=score,
        level=nivel_desde_score(score),
    )


def _score(input: EvaluationInput, age: float) -> float:
    """
    Port literal del árbol. Devuelve el score crudo.
    """

    ap_hi = input.ap_hi
    ap_lo = input.ap_lo
    weight = input.weight
    height = input.height
    cholesterol = input.cholesterol
    gluc = input.gluc
    smoke = input.smoke
    alco = input.alco
    active = input.active

    if ap_hi <= 129.5:
        if age <= 52.5:
            if cholesterol <= 2.5:
                if age <= 43.5:
                    if ap_hi <= 114.5:
                        if cholesterol <= 1.5:
                            return 20.28
                        else:
                            return 34.84
                    else:
                        if cholesterol <= 1.5:
                            return 30.15
                        else:
                            return 45.35
                else:
                    if ap_hi <= 118.5:
                        if weight <= 64.5:
                            return 26.33
                        else:
                            return 35.90
                    else:
                        if cholesterol <= 1.5:
                            return 40.18
                        else:
                            return 50.76
            else:
                if gluc <= 2.5:
                    if ap_lo <= 79.5:
                        if age <= 41.5:
                            return 56.20
                        else:
                            return 70.03
                    else:
                        if weight <= 73.5:
                            return 74.17
                        else:
                            return 81.92
                else:
                    if age <= 40.5:
                        if ap_hi <= 105:
                            return 18.67
                        else:
                            return 45.14
                    else:
                        if ap_lo <= 77:
                            return 51.14
                        else:
                            return 65.76
        else:
            if cholesterol <= 2.5:
                if age <= 60.5:
                    if ap_hi <= 119.5:
                        if weight <= 64.25:
                            return 38.41
                        else:
                            return 48.07
                    else:
                        if age <= 54.5:
                            return 48.87
                        else:
                            return 57.21
                else:
                    if ap_lo <= 78.5:
                        if weight <= 54.5:
                            return 44.64
                        else:
                            return 60.03
                    else:
                        if active <= 0.5:
                            return 70.81
                        else:
                            return 64.91
            else:
                if gluc <= 2.5:
                    if ap_hi <= 102.5:
                        if alco <= 0.5:
                            return 70.99
                        else:
                            return 53.14
                    else:
                        if height <= 185.5:
                            return 82.49
                        else:
                            return 48.12
                else:
                    if age <= 60.5:
                        if weight <= 77.5:
                            return 69.32
                        else:
                            return 77.30
                    else:
                        if weight <= 65.5:
                            return 79.05
                        else:
                            return 83.16
    else:
        if ap_hi <= 138.5:
            if cholesterol <= 2.5:
                if age <= 58.5:
                    if ap_lo <= 89.5:
                        if smoke <= 0.5:
                            return 66.14
                        else:
                            return 56.68
                    else:
                        if smoke <= 0.5:
                            return 74.17
                        else:
                            return 65.12
                else:
                    if smoke <= 0.5:
                        if ap_lo <= 88.5:
                            return 75.11
                        else:
                            return 78.50
                    else:
                        if ap_lo <= 82.5:
                            return 67.15
                        else:
                            return 71.84
            else:
                if smoke <= 0.5:
                    if gluc <= 2.5:
                        if height <= 178.5:
                            return 87.65
                        else:
                            return 82.27
                    else:
                        if age <= 60.5:
                            return 83.68
                        else:
                            return 87.66
                else:
                    if weight <= 62.5:
                        return 63.30
                    else:
                        if height <= 179.5:
                            return 82.99
                        else:
                            return 74.53
        else:
            if ap_lo <= 86.5:
                if ap_lo <= 68.5:
                    if ap_hi <= 249.5:
                        if age <= 59.5:
                            return 75.11
                        else:
                            return 84.35
                    else:
                        return 45.18
                else:
                    if cholesterol <= 1.5:
                        if age <= 53.5:
                            return 84.98
                        else:
                            return 87.79
                    else:
                        if weight <= 55.5:
                            return 82.09
                        else:
                            return 89.28
            else:
                if ap_hi <= 148.5:
                    if gluc <= 2.5:
                        if weight <= 54.5:
                            return 86.92
                        else:
                            return 90.43
                    else:
                        if age <= 41.5:
                            return 77.14
                        else:
                            return 87.32
                else:
                    if weight <= 43.5:
                        return 71.79
                    else:
                        if gluc <= 2.5:
                            return 91.88
                        else:
                            return 89.99