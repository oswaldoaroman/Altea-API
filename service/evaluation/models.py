"""
Modelos de datos del motor de evaluación.

Estos DTOs son el contrato compartido entre:
- Flutter (offline, formulario)
- Backend Python (online, chatbot)

Cualquier cambio aquí DEBE replicarse en Dart.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ==========================================================
# INPUT
# ==========================================================

@dataclass(frozen=True)
class EvaluationInput:
    """
    Datos de entrada del motor.

    Todos los campos son requeridos y no nulos.
    Los categóricos (cholesterol, gluc, active) son floats,
    no enteros, porque el motor compara contra umbrales
    decimales (2.5, 0.5, etc.).

    La edad NO va aquí: es un parámetro separado de `evaluar()`,
    porque es un dato derivado (de fecha de nacimiento).
    """

    ap_hi: float
    ap_lo: float
    weight: float
    height: float
    cholesterol: float
    gluc: float
    smoke: float
    alco: float
    active: float

    def to_dict(self) -> dict:
        return {
            "ap_hi": self.ap_hi,
            "ap_lo": self.ap_lo,
            "weight": self.weight,
            "height": self.height,
            "cholesterol": self.cholesterol,
            "gluc": self.gluc,
            "smoke": self.smoke,
            "alco": self.alco,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EvaluationInput":
        return cls(
            ap_hi=float(d["ap_hi"]),
            ap_lo=float(d["ap_lo"]),
            weight=float(d["weight"]),
            height=float(d["height"]),
            cholesterol=float(d["cholesterol"]),
            gluc=float(d["gluc"]),
            smoke=float(d["smoke"]),
            alco=float(d["alco"]),
            active=float(d["active"]),
        )


# ==========================================================
# RESULT
# ==========================================================

@dataclass(frozen=True)
class EvaluationResult:
    """
    Resultado del motor.

    score:
        Número crudo que devuelve el árbol (18..91 aprox).

    level:
        Categoría derivada del score. Ver levels.py.

    factors:
        Lista de factores detectados (derivados del input).
        Se llena en un paso posterior.

    recommendations:
        Lista de recomendaciones (derivadas del nivel + factores).
        Se llena en un paso posterior.
    """

    score: float
    level: str
    factors: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "level": self.level,
            "factors": list(self.factors),
            "recommendations": list(self.recommendations),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EvaluationResult":
        return cls(
            score=float(d["score"]),
            level=str(d["level"]),
            factors=list(d.get("factors", [])),
            recommendations=list(d.get("recommendations", [])),
        )