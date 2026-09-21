"""
Validación de tipos y rangos para los campos de evaluación.

Este módulo es puro:
- Sin IO.
- Sin FastAPI.
- Sin Ollama.
- Sin SQLAlchemy.

Se usa desde el SlotExtractor y desde el ConversationManager
para garantizar que los datos que llegan al motor son válidos.
"""

from __future__ import annotations

from typing import Any


# ==========================================================
# CAMPOS
# ==========================================================

CAMPOS_EVALUACION = {
    "fuma",
    "consumeAlcohol",
    "actividadFisica",
    "presionSistolica",
    "presionDiastolica",
    "glucosa",
    "colesterol",
    "peso",
    "altura",
}


CAMPOS_REQUERIDOS = {
    "fuma",
    "consumeAlcohol",
    "actividadFisica",
    "presionSistolica",
    "presionDiastolica",
    "glucosa",
    "colesterol",
    "peso",
    "altura",
}


CAMPOS_BOOLEANOS = {"fuma", "consumeAlcohol"}

CAMPOS_ENTEROS = {"actividadFisica"}  # glucosa/colesterol ahora pueden ser float

CAMPOS_DECIMALES = {
    "presionSistolica",
    "presionDiastolica",
    "peso",
    "altura",
    "glucosa",
    "colesterol",
}


# ==========================================================
# VALIDACIÓN
# ==========================================================

def validar_dato(
    field: str,
    value: Any,
) -> tuple[bool, Any, str | None]:
    """
    Valida un valor para un campo de evaluación.

    Devuelve `(ok, valor_normalizado, mensaje_error)`.

    - Si `ok` es True, `valor_normalizado` es el valor listo para
      usarse (tipo correcto, dentro de rango).
    - Si `ok` es False, `mensaje_error` explica qué falló.
    """

    if field not in CAMPOS_EVALUACION:
        return False, None, f"Campo de evaluación desconocido: '{field}'."

    # ------------------------------------------------------
    # Booleanos
    # ------------------------------------------------------

    if field in CAMPOS_BOOLEANOS:
        if not isinstance(value, bool):
            return False, None, f"El campo '{field}' debe ser booleano."
        return True, value, None

    # ------------------------------------------------------
    # Enteros
    # ------------------------------------------------------

    if field in CAMPOS_ENTEROS:
        if isinstance(value, bool) or not isinstance(value, int):
            return False, None, f"El campo '{field}' debe ser entero."
        if value < 0:
            return False, None, f"El campo '{field}' no puede ser negativo."
        return True, value, None

    # ------------------------------------------------------
    # Decimales
    # ------------------------------------------------------

    if field in CAMPOS_DECIMALES:
        if isinstance(value, bool):
            return False, None, f"El campo '{field}' debe ser numérico."
        if not isinstance(value, (int, float)):
            return False, None, f"El campo '{field}' debe ser numérico."
        value = float(value)
        if value < 0:
            return False, None, f"El campo '{field}' no puede ser negativo."
        return True, value, None

    return False, None, "Tipo de dato no soportado."