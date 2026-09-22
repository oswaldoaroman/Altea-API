"""
Tests básicos de los prompts.

No se verifica el texto exacto (cambia a menudo), solo que
los prompts contengan la información clave.
"""

from service.conversation.prompts import (
    SYSTEM_PROMPT_BASE,
    prompt_chat,
    prompt_explicar_resultado,
    prompt_preguntar_slot,
)


# ==========================================================
# SYSTEM PROMPT
# ==========================================================

def test_system_prompt_menciona_altea():
    assert "Altea" in SYSTEM_PROMPT_BASE


def test_system_prompt_menciona_espanol():
    assert "español" in SYSTEM_PROMPT_BASE.lower()


def test_system_prompt_no_menciona_tags_internos():
    assert "<EVAL_DATA>" not in SYSTEM_PROMPT_BASE
    assert "<EVAL_COMPLETE>" not in SYSTEM_PROMPT_BASE
    assert "<EVAL_START>" not in SYSTEM_PROMPT_BASE


def test_system_prompt_menciona_salud():
    assert "salud" in SYSTEM_PROMPT_BASE.lower()


# ==========================================================
# CHAT
# ==========================================================

def test_prompt_chat_contiene_mensaje():
    prompt = prompt_chat(
        mensaje="¿Qué es el riesgo cardiovascular?",
        historial=[],
    )
    assert "¿Qué es el riesgo cardiovascular?" in prompt


def test_prompt_chat_contiene_historial():
    prompt = prompt_chat(
        mensaje="sí",
        historial=[
            {"role": "usuario", "content": "hola"},
            {"role": "altea", "content": "hola, ¿en qué te ayudo?"},
        ],
    )
    assert "hola" in prompt
    assert "¿en qué te ayudo?" in prompt


def test_prompt_chat_sin_historial_no_falla():
    prompt = prompt_chat(mensaje="hola", historial=[])
    assert isinstance(prompt, str)
    assert len(prompt) > 0


# ==========================================================
# PREGUNTAR SLOT
# ==========================================================

def test_prompt_preguntar_slot_menciona_campo():
    prompt = prompt_preguntar_slot(
        field="peso",
        datos_ya={},
        historial=[],
    )
    assert "peso" in prompt.lower()


def test_prompt_preguntar_slot_menciona_datos_previos():
    prompt = prompt_preguntar_slot(
        field="altura",
        datos_ya={"peso": 76.0},
        historial=[],
    )
    assert "altura" in prompt.lower()
    assert "76" in prompt


def test_prompt_preguntar_slot_sin_datos_previos():
    prompt = prompt_preguntar_slot(
        field="peso",
        datos_ya={},
        historial=[],
    )
    assert "ninguno" in prompt.lower() or "sin" in prompt.lower()


def test_prompt_preguntar_slot_campo_desconocido():
    # No debe fallar si el campo no está en el mapeo.
    prompt = prompt_preguntar_slot(
        field="campo_raro",
        datos_ya={},
        historial=[],
    )
    assert "campo_raro" in prompt


def test_prompt_preguntar_slot_no_incluye_tags():
    prompt = prompt_preguntar_slot(
        field="peso",
        datos_ya={},
        historial=[],
    )
    assert "<EVAL_DATA>" not in prompt
    assert "<EVAL_COMPLETE>" not in prompt


# ==========================================================
# EXPLICAR RESULTADO
# ==========================================================

def test_prompt_explicar_resultado_menciona_nivel():
    prompt = prompt_explicar_resultado(
        score=66.14,
        level="alto",
        datos={"peso": 76.0},
    )
    assert "alto" in prompt.lower()


def test_prompt_explicar_resultado_menciona_score():
    prompt = prompt_explicar_resultado(
        score=66.14,
        level="alto",
        datos={},
    )
    assert "66.14" in prompt


def test_prompt_explicar_resultado_menciona_datos():
    prompt = prompt_explicar_resultado(
        score=50.0,
        level="moderado",
        datos={"peso": 76.0, "altura": 175.0},
    )
    assert "76" in prompt
    assert "175" in prompt


def test_prompt_explicar_resultado_sin_datos_no_falla():
    prompt = prompt_explicar_resultado(
        score=20.0,
        level="bajo",
        datos={},
    )
    assert isinstance(prompt, str)
    assert len(prompt) > 0