"""
Cortes de score → nivel de riesgo.

IMPORTANTE:
Estos cortes son provisionales, definidos a partir de la
distribución observada del árbol de decisión. No son clínicos.

Si en el futuro se definen cortes validados por un profesional
de la salud, reemplazar aquí.
"""

from __future__ import annotations


# ==========================================================
# CORTES
# ==========================================================

# (umbral_superior_exclusivo, nombre_del_nivel)
# El orden importa: se evalúa de menor a mayor.
CUTS = [
    (30.0, "bajo"),
    (55.0, "moderado"),
    (75.0, "alto"),
    (float("inf"), "muy_alto"),
]


def nivel_desde_score(score: float) -> str:
    """
    Devuelve el nombre del nivel para un score dado.

    Ejemplos:
        20.28 → "bajo"
        45.35 → "moderado"
        70.03 → "alto"
        85.00 → "muy_alto"
    """

    for umbral, nombre in CUTS:
        if score < umbral:
            return nombre

    return "muy_alto"  # fallback, no debería alcanzarse