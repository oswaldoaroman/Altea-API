"""
Fallbacks sintéticos para campos que el usuario no sabe.

Cuando el usuario no sabe un dato tras varios reintentos,
se genera un valor plausible para no bloquear la evaluación.

IMPORTANTE:
- Estos valores NO son clínicos. Son estimaciones.
- Se documentan como tales.
- El motor los usa igual que si el usuario los hubiera dado.
"""

from __future__ import annotations


# ==========================================================
# PRESIÓN
# ==========================================================

def convertir_presion(
    categoria: int,
    edad: int,
    peso: float,
) -> tuple[float, float]:
    """
    Convierte una categoría de presión (1, 2, 3) a un par
    (sistólica, diastólica) estimado.

    Portado del `EvaluationMapper.convertirPresion` en Dart.

    ⚠️ ESTA ES UNA ESTIMACIÓN SINTÉTICA, NO CLÍNICA.

    Categorías:
        1 = baja
        2 = normal
        3 = alta
    """

    seed = edad + int(peso)

    if categoria == 1:
        return (
            110.0 + (seed % 20),
            70.0 + (seed % 15),
        )

    if categoria == 2:
        return (
            130.0 + (seed % 10),
            85.0 + (seed % 5),
        )

    if categoria == 3:
        return (
            140.0 + (seed % 20),
            90.0 + (seed % 10),
        )

    # Fallback por defecto.
    return (120.0, 80.0)


# ==========================================================
# GLUCOSA — categoría
# ==========================================================

def categoria_glucosa(mgdl: float) -> float:
    """
    Convierte un valor real de glucosa (mg/dL) a categoría 1/2/3.

    Umbrales (acordados):
        < 100  → 1 (normal)
        100-125 → 2 (elevada)
        ≥ 126  → 3 (alta)
    """

    if mgdl < 100:
        return 1.0
    if mgdl < 126:
        return 2.0
    return 3.0


# ==========================================================
# COLESTEROL — categoría
# ==========================================================

def categoria_colesterol(mgdl: float) -> float:
    """
    Convierte un valor real de colesterol (mg/dL) a categoría 1/2/3.

    Umbrales (acordados):
        < 200   → 1 (normal)
        200-239 → 2 (elevado)
        ≥ 240   → 3 (alto)
    """

    if mgdl < 200:
        return 1.0
    if mgdl < 240:
        return 2.0
    return 3.0


# ==========================================================
# CATEGORÍA A DESCRIPCIÓN (para preguntar al usuario)
# ==========================================================

CATEGORIAS_GLUCOSA = {
    1: "normal",
    2: "elevada",
    3: "alta",
}

CATEGORIAS_COLESTEROL = {
    1: "normal",
    2: "elevado",
    3: "alto",
}

CATEGORIAS_PRESION = {
    1: "baja",
    2: "normal",
    3: "alta",
}


# ==========================================================
# DETECCIÓN DE CATEGORÍA EN TEXTO
# ==========================================================

def parsear_categoria(texto: str, campo: str) -> int | None:
    """
    Dado un texto del usuario y un campo, extrae la categoría (1, 2, 3)
    según palabras clave.

    `campo` debe ser "glucosa", "colesterol" o "presion".

    Devuelve 1, 2 o 3 si detecta, o None si no.
    """

    if not texto:
        return None

    t = texto.lower().strip()

    # Normalizar tildes mínimas.
    t = t.replace("í", "i").replace("á", "a").replace("é", "e").replace("ó", "o").replace("ú", "u")

    # ------------------------------------------------------
    # PRESIÓN
    # ------------------------------------------------------

    if campo == "presion":
        if "baja" in t or "bajo" in t:
            return 1
        if "alta" in t or "alto" in t:
            return 3
        if "normal" in t or "media" in t or "medio" in t:
            return 2
        return None

    # ------------------------------------------------------
    # GLUCOSA
    # ------------------------------------------------------

    if campo == "glucosa":
        if "alta" in t or "alto" in t or "muy alta" in t or "muy alto" in t:
            return 3
        if "elevada" in t or "elevado" in t:
            return 2
        if "normal" in t or "bien" in t:
            return 1
        return None

    # ------------------------------------------------------
    # COLESTEROL
    # ------------------------------------------------------

    if campo == "colesterol":
        if "alta" in t or "alto" in t or "muy alta" in t or "muy alto" in t:
            return 3
        if "elevado" in t or "elevada" in t:
            return 2
        if "normal" in t or "bien" in t:
            return 1
        return None

    return None