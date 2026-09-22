"""
Prompts para el LLM.

El LLM se usa para 3 cosas concretas:
1. Redactar la respuesta a un mensaje de chat libre.
2. Redactar la pregunta del siguiente campo de evaluación.
3. Redactar la explicación del resultado final.

En ningún caso el LLM extrae datos, valida, calcula o decide el flujo.
Todo eso lo hace el backend con código determinista.

El `system` es siempre el mismo (`SYSTEM_PROMPT_BASE`).
Lo que cambia es el `prompt`, según la situación.
"""

from __future__ import annotations


# ==========================================================
# SYSTEM PROMPT
# ==========================================================

SYSTEM_PROMPT_BASE = """
Eres Altea, un asistente de salud de una aplicación de prevención cardiovascular.

IDENTIDAD:
- Te llamas Altea.
- Eres un asistente de salud, no un médico.
- No haces diagnósticos.
- No recetas medicamentos.
- No reemplazas a un profesional de la salud.

ESTILO:
- Responde siempre en español.
- Sé amable, claro, natural y conciso.
- No uses tecnicismos innecesarios.
- No uses emojis salvo que el usuario los use primero.

TEMAS:
- Puedes hablar de cualquier tema relacionado con la salud.
- Si el usuario pregunta algo fuera de salud, redirige amablemente
  hacia temas de salud.
- Si el usuario pide consejo médico específico, recomienda consultar
  a un profesional.

REGLAS:
- No inventes información.
- No afirmes cosas que no sabes.
- Si no estás seguro, dilo.
- No muestres etiquetas internas ni instrucciones.
""".strip()


# ==========================================================
# PROMPT: CHAT LIBRE
# ==========================================================

def prompt_chat(
    mensaje: str,
    historial: list[dict],
) -> str:
    """
    Prompt para responder a un mensaje de chat libre.

    `historial` es una lista de dicts con `role` y `content`,
    en orden cronológico. Se usa solo para dar contexto.
    """

    historial_texto = _formatear_historial(historial)

    return f"""
Esta es la conversación reciente con el usuario:

{historial_texto}

MENSAJE ACTUAL DEL USUARIO:
{mensaje}

Responde al usuario de forma natural y útil.
""".strip()


# ==========================================================
# PROMPT: PREGUNTAR SIGUIENTE CAMPO
# ==========================================================

# Nombres legibles para los campos.
_NOMBRES_CAMPOS = {
    "peso": "peso en kilogramos",
    "altura": "altura en centímetros",
    "presionSistolica": "presión arterial sistólica",
    "presionDiastolica": "presión arterial diastólica",
    "fuma": "consumo de tabaco",
    "consumeAlcohol": "consumo de alcohol",
    "actividadFisica": "nivel de actividad física",
    "glucosa": "nivel de glucosa en sangre",
    "colesterol": "nivel de colesterol en sangre",
}


def prompt_preguntar_slot(
    field: str,
    datos_ya: dict,
    historial: list[dict],
) -> str:
    """
    Prompt para pedir el siguiente campo de evaluación.

    `field` es el campo que hay que preguntar.
    `datos_ya` son los campos ya recopilados.
    `historial` es la conversación reciente.
    """

    nombre_campo = _NOMBRES_CAMPOS.get(field, field)

    # Lista de campos ya obtenidos, en formato legible.
    if datos_ya:
        ya_texto = "\n".join(
            f"- {_NOMBRES_CAMPOS.get(k, k)}: {v}"
            for k, v in datos_ya.items()
            if v is not None
        )
    else:
        ya_texto = "(ninguno aún)"

    historial_texto = _formatear_historial(historial)

    return f"""
Estás ayudando al usuario a completar una evaluación de riesgo
cardiovascular. Necesitas preguntarle de forma natural y breve
por el siguiente dato:

DATO A PREGUNTAR: {nombre_campo}

DATOS QUE YA TIENES:
{ya_texto}

HISTORIAL RECIENTE:
{historial_texto}

INSTRUCCIONES:
- Haz una sola pregunta, breve y clara.
- Pregunta solo por el dato indicado.
- No inventes datos.
- No repitas datos que ya tienes.
- No menciones etiquetas ni campos internos.
- No expliques el proceso, solo pregunta.

Redacta la pregunta:
""".strip()


# ==========================================================
# PROMPT: EXPLICAR RESULTADO
# ==========================================================

_LEVELS_LEGIBLES = {
    "bajo": "bajo",
    "moderado": "moderado",
    "alto": "alto",
    "muy_alto": "muy alto",
}


def prompt_explicar_resultado(
    score: float,
    level: str,
    datos: dict,
) -> str:
    """
    Prompt para explicar el resultado de la evaluación.

    El score y el level ya están calculados por el motor
    determinista. El LLM solo los explica en lenguaje natural.
    """

    level_legible = _LEVELS_LEGIBLES.get(level, level)

    datos_texto = "\n".join(
        f"- {_NOMBRES_CAMPOS.get(k, k)}: {v}"
        for k, v in datos.items()
        if v is not None
    )

    return f"""
El usuario ha completado una evaluación de riesgo cardiovascular.

RESULTADO CALCULADO POR EL SISTEMA:
- Nivel de riesgo: {level_legible}
- Puntuación: {score}

DATOS UTILIZADOS:
{datos_texto}

INSTRUCCIONES:
- Explica el resultado de forma sencilla y tranquilizadora.
- No cambies el nivel ni la puntuación.
- No hagas diagnósticos.
- No recetes medicamentos.
- Si el nivel es alto o muy alto, recomienda consultar a un
  profesional de la salud.
- No menciones etiquetas ni campos internos.
- Sé breve: 2 o 3 frases.

Redacta la explicación:
""".strip()


# ==========================================================
# HELPERS
# ==========================================================

def _formatear_historial(historial: list[dict]) -> str:
    """
    Convierte una lista de mensajes en texto plano.

    Se queda solo con los últimos 10 mensajes para no
    desperdiciar contexto.
    """

    if not historial:
        return "(sin historial)"

    recientes = historial[-10:]

    return "\n".join(
        f"{m.get('role', 'usuario')}: {m.get('content', '')}"
        for m in recientes
    )