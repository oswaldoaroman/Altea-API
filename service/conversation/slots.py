"""
Extractor determinista de slots a partir de texto libre del usuario.

Estrategia:
1. Aplicar regex para detectar los campos claramente identificables.
2. Devolver la lista de slots encontrados (field, value).
3. NO delegar al LLM aquí. Si el extractor no detecta nada, el
   `ConversationManager` decide si llamar al LLM como fallback.

Este módulo es puro:
- Sin IO.
- Sin estado.
- Sin dependencias de FastAPI, Ollama, SQLAlchemy.
- Testeable con funciones puras.
"""

from __future__ import annotations

import re
from typing import Any

from .validators import CAMPOS_EVALUACION, validar_dato


# ==========================================================
# TIPOS
# ==========================================================

# Un slot extraído es una tupla (field, value).
Slot = tuple[str, Any]


# ==========================================================
# REGEX BASE
# ==========================================================

# Números decimales o enteros. Acepta coma o punto.
_NUM = r"(\d+(?:[.,]\d+)?)"


# ==========================================================
# PESO
# ==========================================================

# "Peso 76 kilos", "Peso 76 kg", "Peso 76", "Mi peso es de 76",
# "Peso: 76"
_PESO_PATTERNS = [
    re.compile(rf"\bpeso\b[^\d]{{0,10}}{_NUM}", re.IGNORECASE),
    re.compile(rf"mi peso es\s+(?:de\s+)?{_NUM}", re.IGNORECASE),
    re.compile(rf"\bpeso\b\s*[:=]\s*{_NUM}", re.IGNORECASE),
    re.compile(rf"{_NUM}\s*(?:kg|kilos|kilogramos)\b", re.IGNORECASE),
]


# ==========================================================
# ALTURA
# ==========================================================

# "Mido 1.75 metros", "Mido 175 cm", "Mi estatura es 1.75",
# "Tengo una altura de 175", "1.75 m", "175 cm"
_ALTURA_PATTERNS = [
    re.compile(rf"\bmido\b[^\d]{{0,10}}{_NUM}", re.IGNORECASE),
    re.compile(rf"\bestatura\b[^\d]{{0,10}}{_NUM}", re.IGNORECASE),
    re.compile(rf"\baltura\b[^\d]{{0,10}}{_NUM}", re.IGNORECASE),
    re.compile(rf"{_NUM}\s*(?:cm|cent[ií]metros)\b", re.IGNORECASE),
    re.compile(rf"{_NUM}\s*(?:m|metros)\b", re.IGNORECASE),
]


# ==========================================================
# PRESIÓN
# ==========================================================

# "130/85", "130 sobre 85", "presión 130/85",
# "sistólica 130", "diastólica 85"
_PRESION_PATTERNS = [
    # "presión ... 130/85" o "130/85 de presión" o simplemente "130/85"
    re.compile(rf"\b{_NUM}\s*(?:/|sobre)\s*{_NUM}\b", re.IGNORECASE),
]

# Detecta "130 de sistólica", "130 sistólica", "sistólica 130", "sistólica es 130"
_PRESION_SISTOLICA_PATTERN = re.compile(
    rf"(?:"
    rf"{_NUM}\s*(?:de\s+|como\s+)?sist[oó]lica"
    rf"|"
    rf"sist[oó]lica\s*(?:es|de|en|:)?\s*{_NUM}"
    rf")",
    re.IGNORECASE,
)

# Detecta "85 de diastólica", "85 diastólica", "diastólica 85", "diastólica es 85"
_PRESION_DIASTOLICA_PATTERN = re.compile(
    rf"(?:"
    rf"{_NUM}\s*(?:de\s+|como\s+)?diast[oó]lica"
    rf"|"
    rf"diast[oó]lica\s*(?:es|de|en|:)?\s*{_NUM}"
    rf")",
    re.IGNORECASE,
)


# ==========================================================
# FUMA
# ==========================================================

# Detección de booleanos. Estrategia: buscar negaciones primero.
_FUMA_NEGATIVO = re.compile(
    r"\b(no\s+fumo|no\s+soy\s+fumador|dej[eé]\s+de\s+fumar|"
    r"nunca\s+he\s+fumado|no\s+fumador)\b",
    re.IGNORECASE,
)

_FUMA_POSITIVO = re.compile(
    r"\b(s[ií],?\s*fumo|soy\s+fumador|fumo|fumador|"
    r"consumo\s+tabaco|tomo\s+cigarrillo)\b",
    re.IGNORECASE,
)


# ==========================================================
# ALCOHOL
# ==========================================================

_ALCOHOL_NEGATIVO = re.compile(
    r"\b(no\s+tomo\s+alcohol|no\s+consumo\s+(?:alcohol|bebidas\s+alcoh[oó]licas)|"
    r"no\s+bebo|nunca\s+tomo)\b",
    re.IGNORECASE,
)

_ALCOHOL_POSITIVO = re.compile(
    r"\b(s[ií],?\s*(?:tomo|consumo|bebo)\s+alcohol|"
    r"tomo\s+alcohol|consumo\s+alcohol|bebo\s+alcohol|"
    r"alcohol\s+ocasional|consumo\s+ocasional|bebo\s+ocasionalmente)\b",
    re.IGNORECASE,
)


# ==========================================================
# ACTIVIDAD FÍSICA
# ==========================================================

_ACTIVIDAD_SEDENTARIO = re.compile(
    r"\b(sedentario|no\s+hago\s+ejercicio|no\s+hago\s+actividad|"
    r"casi\s+no\s+hago\s+ejercicio|nada\s+de\s+ejercicio)\b",
    re.IGNORECASE,
)

_ACTIVIDAD_ACTIVO = re.compile(
    r"\b(hago\s+ejercicio\s+(?:regularmente|todos\s+los\s+d[ií]as|frecuentemente)|"
    r"soy\s+activo|muy\s+activo)\b",
    re.IGNORECASE,
)

_ACTIVIDAD_MODERADO = re.compile(
    r"\b(hago\s+ejercicio|hago\s+actividad\s+f[ií]sica|"
    r"actividad\s+moderada|a\s+veces\s+hago\s+ejercicio)\b",
    re.IGNORECASE,
)


# ==========================================================
# GLUCOSA
# ==========================================================

_GLUCOSA_PATTERNS = [
    re.compile(rf"\bglucosa\b[^\d]{{0,10}}{_NUM}", re.IGNORECASE),
    re.compile(rf"\baz[uú]car\b[^\d]{{0,10}}{_NUM}", re.IGNORECASE),
    re.compile(rf"{_NUM}\s*(?:mg/dl|de\s+glucosa)", re.IGNORECASE),
]


# ==========================================================
# COLESTEROL
# ==========================================================

_COLESTEROL_PATTERNS = [
    re.compile(rf"\bcolesterol\b[^\d]{{0,10}}{_NUM}", re.IGNORECASE),
    re.compile(rf"{_NUM}\s*(?:mg/dl|de\s+colesterol)", re.IGNORECASE),
]


# ==========================================================
# API PÚBLICA
# ==========================================================

def extraer_slots(texto: str) -> list[Slot]:
    """
    Extrae todos los slots detectables del texto del usuario.

    Devuelve una lista de tuplas `(field, value)`.
    Los valores ya están validados (tipo correcto, rango correcto).
    Los slots con valor inválido NO se devuelven aquí; el
    `ConversationManager` puede decidir si emitir un error.
    """

    if not texto or not texto.strip():
        return []

    texto = texto.strip()
    slots: list[Slot] = []

    # ------------------------------------------------------
    # PESO
    # ------------------------------------------------------

    peso = _extraer_peso(texto)
    if peso is not None:
        slots.append(("peso", peso))

    # ------------------------------------------------------
    # ALTURA
    # ------------------------------------------------------

    altura = _extraer_altura(texto)
    if altura is not None:
        slots.append(("altura", altura))

    # ------------------------------------------------------
    # PRESIÓN (par sistólica/diastólica)
    # ------------------------------------------------------

    presion = _extraer_presion(texto)
    if presion is not None:
        slots.append(("presionSistolica", presion[0]))
        slots.append(("presionDiastolica", presion[1]))

    # ------------------------------------------------------
    # FUMA
    # ------------------------------------------------------

    fuma = _extraer_fuma(texto)
    if fuma is not None:
        slots.append(("fuma", fuma))

    # ------------------------------------------------------
    # ALCOHOL
    # ------------------------------------------------------

    alcohol = _extraer_alcohol(texto)
    if alcohol is not None:
        slots.append(("consumeAlcohol", alcohol))

    # ------------------------------------------------------
    # ACTIVIDAD FÍSICA
    # ------------------------------------------------------

    actividad = _extraer_actividad(texto)
    if actividad is not None:
        slots.append(("actividadFisica", actividad))

    # ------------------------------------------------------
    # GLUCOSA
    # ------------------------------------------------------

    glucosa = _extraer_glucosa(texto)
    if glucosa is not None:
        slots.append(("glucosa", glucosa))

    # ------------------------------------------------------
    # COLESTEROL
    # ------------------------------------------------------

    colesterol = _extraer_colesterol(texto)
    if colesterol is not None:
        slots.append(("colesterol", colesterol))

    # ------------------------------------------------------
    # VALIDACIÓN FINAL
    # ------------------------------------------------------

    slots_validados: list[Slot] = []

    for field, value in slots:
        ok, valor_ok, _ = validar_dato(field, value)

        if ok:
            slots_validados.append((field, valor_ok))

    return slots_validados


# ==========================================================
# EXTRACTORES INTERNOS
# ==========================================================

def _normalizar_numero(raw: str) -> float:
    """Convierte '76' o '1,75' a float."""
    return float(raw.replace(",", "."))


def _extraer_peso(texto: str) -> float | None:
    for pattern in _PESO_PATTERNS:
        match = pattern.search(texto)
        if match:
            valor = _normalizar_numero(match.group(1))
            # Validación rápida de rango plausible.
            if 20 <= valor <= 300:
                return valor
    return None


def _extraer_altura(texto: str) -> float | None:
    for pattern in _ALTURA_PATTERNS:
        match = pattern.search(texto)
        if match:
            valor = _normalizar_numero(match.group(1))

            # Si el valor es < 3, interpretar como metros.
            if 0.5 <= valor <= 3.0:
                valor = valor * 100.0

            # Validación de rango plausible (50 cm a 250 cm).
            if 50 <= valor <= 250:
                return valor
    return None


def _extraer_presion(texto: str) -> tuple[float, float] | None:
    # Primero intentamos con "sistólica" y "diastólica" explícitas.
    sistolica_match = _PRESION_SISTOLICA_PATTERN.search(texto)
    diastolica_match = _PRESION_DIASTOLICA_PATTERN.search(texto)

    if sistolica_match and diastolica_match:
        sistolica = _normalizar_numero(sistolica_match.group(1))
        diastolica = _normalizar_numero(diastolica_match.group(1))
        if _presion_plausible(sistolica, diastolica):
            return (sistolica, diastolica)

    # Si no, buscamos "130/85" o "130 sobre 85".
    for pattern in _PRESION_PATTERNS:
        match = pattern.search(texto)
        if match:
            sistolica = _normalizar_numero(match.group(1))
            diastolica = _normalizar_numero(match.group(2))
            if _presion_plausible(sistolica, diastolica):
                return (sistolica, diastolica)

    return None


def _presion_plausible(sistolica: float, diastolica: float) -> bool:
    return (
        60 <= diastolica <= 150
        and 90 <= sistolica <= 250
        and sistolica > diastolica
    )


def _extraer_fuma(texto: str) -> bool | None:
    # Negación primero (más específica).
    if _FUMA_NEGATIVO.search(texto):
        return False

    if _FUMA_POSITIVO.search(texto):
        return True

    return None


def _extraer_alcohol(texto: str) -> bool | None:
    if _ALCOHOL_NEGATIVO.search(texto):
        return False

    if _ALCOHOL_POSITIVO.search(texto):
        return True

    return None


def _extraer_actividad(texto: str) -> int | None:
    if _ACTIVIDAD_SEDENTARIO.search(texto):
        return 2

    if _ACTIVIDAD_ACTIVO.search(texto):
        return 0

    if _ACTIVIDAD_MODERADO.search(texto):
        return 1

    return None


def _extraer_glucosa(texto: str) -> float | None:
    for pattern in _GLUCOSA_PATTERNS:
        match = pattern.search(texto)
        if match:
            valor = _normalizar_numero(match.group(1))
            if 30 <= valor <= 600:
                return valor
    return None


def _extraer_colesterol(texto: str) -> float | None:
    for pattern in _COLESTEROL_PATTERNS:
        match = pattern.search(texto)
        if match:
            valor = _normalizar_numero(match.group(1))
            if 50 <= valor <= 500:
                return valor
    return None