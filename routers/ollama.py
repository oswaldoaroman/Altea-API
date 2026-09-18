import json
from typing import Any

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from database.ollama_config import (
    OLLAMA_MODEL,
    OLLAMA_URL,
    SYSTEM_PROMPT,
)


router = APIRouter(
    prefix="/ollama",
    tags=["Ollama"],
)


# ==========================================================
# CAMPOS DE LA EVALUACIÓN
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
    "glucosa",
    "colesterol",
    "peso",
    "altura",
}


# ==========================================================
# ESTADO DE LA CONVERSACIÓN
# ==========================================================

class ConversationState:

    def __init__(self):
        self.evaluacion_activa = False

        self.datos_evaluacion = {
            "fuma": None,
            "consumeAlcohol": None,
            "actividadFisica": None,
            "presionSistolica": None,
            "presionDiastolica": None,
            "glucosa": None,
            "colesterol": None,
            "peso": None,
            "altura": None,
        }

        self.historial = []

    # ------------------------------------------------------
    # Reiniciar evaluación
    # ------------------------------------------------------

    def iniciar_evaluacion(self):
        self.evaluacion_activa = True

        self.datos_evaluacion = {
            "fuma": None,
            "consumeAlcohol": None,
            "actividadFisica": None,
            "presionSistolica": None,
            "presionDiastolica": None,
            "glucosa": None,
            "colesterol": None,
            "peso": None,
            "altura": None,
        }

    # ------------------------------------------------------
    # Verificar si está completa
    # ------------------------------------------------------

    def evaluacion_completa(self) -> bool:

        return all(
            self.datos_evaluacion[campo] is not None
            for campo in CAMPOS_REQUERIDOS
        )

    # ------------------------------------------------------
    # Datos faltantes
    # ------------------------------------------------------

    def datos_faltantes(self):

        return [
            campo
            for campo in CAMPOS_REQUERIDOS
            if self.datos_evaluacion[campo] is None
        ]


# ==========================================================
# VALIDACIÓN DE DATOS
# ==========================================================

def validar_dato(
    field: str,
    value: Any,
) -> tuple[bool, Any, str | None]:

    if field not in CAMPOS_EVALUACION:
        return False, None, "Campo de evaluación desconocido."

    # ------------------------------------------------------
    # Booleanos
    # ------------------------------------------------------

    if field in {
        "fuma",
        "consumeAlcohol",
    }:

        if not isinstance(value, bool):
            return (
                False,
                None,
                f"El campo '{field}' debe ser booleano.",
            )

        return True, value, None

    # ------------------------------------------------------
    # Enteros
    # ------------------------------------------------------

    if field in {
        "actividadFisica",
        "glucosa",
        "colesterol",
    }:

        # bool es una subclase de int en Python.
        # Por eso se comprueba explícitamente.
        if isinstance(value, bool) or not isinstance(value, int):
            return (
                False,
                None,
                f"El campo '{field}' debe ser entero.",
            )

        if value < 0:
            return (
                False,
                None,
                f"El campo '{field}' no puede ser negativo.",
            )

        return True, value, None

    # ------------------------------------------------------
    # Valores decimales
    # ------------------------------------------------------

    if field in {
        "presionSistolica",
        "presionDiastolica",
        "peso",
        "altura",
    }:

        if isinstance(value, bool):
            return (
                False,
                None,
                f"El campo '{field}' debe ser numérico.",
            )

        if not isinstance(value, (int, float)):
            return (
                False,
                None,
                f"El campo '{field}' debe ser numérico.",
            )

        value = float(value)

        if value < 0:
            return (
                False,
                None,
                f"El campo '{field}' no puede ser negativo.",
            )

        return True, value, None

    return False, None, "Tipo de dato no soportado."


# ==========================================================
# CONSTRUCCIÓN DEL CONTEXTO
# ==========================================================

def construir_contexto_evaluacion(
    estado: ConversationState,
) -> str:

    datos = estado.datos_evaluacion

    return f"""
ESTADO ACTUAL DE LA EVALUACIÓN:

fuma: {datos["fuma"]}
consumeAlcohol: {datos["consumeAlcohol"]}
actividadFisica: {datos["actividadFisica"]}
presionSistolica: {datos["presionSistolica"]}
presionDiastolica: {datos["presionDiastolica"]}
glucosa: {datos["glucosa"]}
colesterol: {datos["colesterol"]}
peso: {datos["peso"]}
altura: {datos["altura"]}

Evaluación activa: {estado.evaluacion_activa}

Datos requeridos faltantes:
{estado.datos_faltantes()}
"""


# ==========================================================
# CONSTRUIR PROMPT
# ==========================================================

def construir_prompt(
    estado: ConversationState,
    mensaje_usuario: str,
) -> str:

    contexto = construir_contexto_evaluacion(estado)

    historial = ""

    # Evitamos enviar un historial excesivamente grande.
    ultimos_mensajes = estado.historial[-10:]

    for mensaje in ultimos_mensajes:

        historial += (
            f'{mensaje["role"]}: '
            f'{mensaje["content"]}\n'
        )

    return f"""
{contexto}

HISTORIAL RECIENTE:
{historial}

MENSAJE ACTUAL DEL USUARIO:
{mensaje_usuario}

Continúa la conversación siguiendo estrictamente tus reglas.
"""


# ==========================================================
# LIMPIAR RESPUESTA DEL MODELO
# ==========================================================

def limpiar_respuesta_visible(
    respuesta: str,
) -> str:

    texto = respuesta

    # Eliminamos completamente los eventos internos.

    while "<EVAL_START>" in texto:
        texto = texto.replace(
            "<EVAL_START>",
            "",
        )

    while "<EVAL_COMPLETE>" in texto:
        texto = texto.replace(
            "<EVAL_COMPLETE>",
            "",
        )

    # Eliminar bloques EVAL_DATA completos.

    while "<EVAL_DATA>" in texto:

        inicio = texto.find("<EVAL_DATA>")

        fin = texto.find(
            "</EVAL_DATA>",
            inicio,
        )

        if fin == -1:
            break

        fin += len("</EVAL_DATA>")

        texto = (
            texto[:inicio]
            + texto[fin:]
        )

    return texto.strip()


# ==========================================================
# PROCESAR EVENTOS DE EVALUACIÓN
# ==========================================================

async def procesar_eventos_evaluacion(
    respuesta: str,
    estado: ConversationState,
    websocket: WebSocket,
):

    # ------------------------------------------------------
    # EVAL_START
    # ------------------------------------------------------

    if "<EVAL_START>" in respuesta:

        estado.iniciar_evaluacion()

        await websocket.send_json({
            "type": "evaluation_start",
        })

    # ------------------------------------------------------
    # EVAL_DATA
    # ------------------------------------------------------

    inicio = 0

    while True:

        inicio_tag = respuesta.find(
            "<EVAL_DATA>",
            inicio,
        )

        if inicio_tag == -1:
            break

        fin_tag = respuesta.find(
            "</EVAL_DATA>",
            inicio_tag,
        )

        if fin_tag == -1:
            break

        contenido = respuesta[
            inicio_tag + len("<EVAL_DATA>"):
            fin_tag
        ].strip()

        try:

            dato = json.loads(contenido)

        except json.JSONDecodeError:

            print(
                "EVAL_DATA inválido:"
                f" {contenido}"
            )

            inicio = (
                fin_tag
                + len("</EVAL_DATA>")
            )

            continue

        field = dato.get("field")
        value = dato.get("value")

        valido, valor_validado, error = validar_dato(
            field,
            value,
        )

        if not valido:

            print(
                f"Dato rechazado: "
                f"{field} = {value}. "
                f"Motivo: {error}"
            )

            await websocket.send_json({
                "type": "evaluation_error",
                "field": field,
                "message": error,
            })

            inicio = (
                fin_tag
                + len("</EVAL_DATA>")
            )

            continue

        # --------------------------------------------------
        # Guardar dato validado
        # --------------------------------------------------

        estado.datos_evaluacion[field] = valor_validado

        await websocket.send_json({
            "type": "evaluation_data",
            "field": field,
            "value": valor_validado,
        })

        inicio = (
            fin_tag
            + len("</EVAL_DATA>")
        )

    # ------------------------------------------------------
    # EVAL_COMPLETE
    # ------------------------------------------------------

    if "<EVAL_COMPLETE>" in respuesta:

        # IMPORTANTE:
        # El LLM NO decide realmente si está completa.
        # El backend lo verifica.

        if estado.evaluacion_completa():

            estado.evaluacion_activa = False

            await websocket.send_json({
                "type": "evaluation_complete",
                "data": estado.datos_evaluacion,
            })

        else:

            campos_faltantes = (
                estado.datos_faltantes()
            )

            print(
                "El modelo intentó completar "
                "una evaluación incompleta."
            )

            await websocket.send_json({
                "type": "evaluation_incomplete",
                "missing": campos_faltantes,
            })


# ==========================================================
# WEBSOCKET
# ==========================================================

@router.websocket("/ws")
async def ollama_websocket(
    websocket: WebSocket,
):

    await websocket.accept()

    print(
        "Cliente WebSocket conectado."
    )

    estado = ConversationState()

    try:

        while True:

            # ==================================================
            # RECIBIR MENSAJE
            # ==================================================

            message = await websocket.receive_text()

            try:

                data = json.loads(message)

            except json.JSONDecodeError:

                await websocket.send_json({
                    "type": "error",
                    "message": (
                        "El mensaje recibido "
                        "no es JSON válido."
                    ),
                })

                continue

            # ==================================================
            # VALIDAR TIPO
            # ==================================================

            tipo = data.get("type")

            if tipo != "message":

                await websocket.send_json({
                    "type": "error",
                    "message": (
                        "Tipo de mensaje no válido."
                    ),
                })

                continue

            # ==================================================
            # OBTENER CONTENIDO
            # ==================================================

            content = data.get("content")

            if not isinstance(content, str):
                content = ""

            content = content.strip()

            if not content:

                await websocket.send_json({
                    "type": "error",
                    "message": (
                        "El mensaje no puede "
                        "estar vacío."
                    ),
                })

                continue

            # ==================================================
            # GUARDAR MENSAJE DEL USUARIO
            # ==================================================

            estado.historial.append({
                "role": "Usuario",
                "content": content,
            })

            # ==================================================
            # CONSTRUIR PROMPT
            # ==================================================

            prompt = construir_prompt(
                estado,
                content,
            )

            # ==================================================
            # PAYLOAD OLLAMA
            # ==================================================

            payload = {
                "model": OLLAMA_MODEL,

                # Prompt contextual.
                "prompt": prompt,

                # El system prompt va separado.
                "system": SYSTEM_PROMPT,

                # Generaremos la respuesta completa
                # para poder procesar correctamente
                # los eventos internos.
                "stream": True,
            }

            respuesta_completa = ""

            # ==================================================
            # COMUNICACIÓN CON OLLAMA
            # ==================================================

            try:

                async with httpx.AsyncClient(
                    timeout=None
                ) as client:

                    async with client.stream(
                        "POST",
                        OLLAMA_URL,
                        json=payload,
                    ) as response:

                        if response.status_code != 200:

                            error_body = (
                                await response.aread()
                            )

                            await websocket.send_json({
                                "type": "error",
                                "message": (
                                    "Error de Ollama: "
                                    f"{error_body.decode()}"
                                ),
                            })

                            continue

                        # ==========================================
                        # RECIBIR STREAM
                        # ==========================================

                        async for line in response.aiter_lines():

                            if not line:
                                continue

                            try:

                                ollama_data = json.loads(
                                    line
                                )

                            except json.JSONDecodeError:

                                continue

                            chunk = (
                                ollama_data.get(
                                    "response",
                                    "",
                                )
                            )

                            if chunk:
                                respuesta_completa += chunk

                            if ollama_data.get(
                                "done"
                            ) is True:

                                break

                # ==================================================
                # PROCESAR EVENTOS INTERNOS
                # ==================================================

                await procesar_eventos_evaluacion(
                    respuesta_completa,
                    estado,
                    websocket,
                )

                # ==================================================
                # LIMPIAR TEXTO PARA EL USUARIO
                # ==================================================

                texto_visible = (
                    limpiar_respuesta_visible(
                        respuesta_completa
                    )
                )

                # ==================================================
                # ENVIAR RESPUESTA VISIBLE
                # ==================================================

                if texto_visible:

                    await websocket.send_json({
                        "type": "chunk",
                        "content": texto_visible,
                    })

                # ==================================================
                # GUARDAR RESPUESTA EN HISTORIAL
                # ==================================================

                estado.historial.append({
                    "role": "Altea",
                    "content": texto_visible,
                })

                # ==================================================
                # FIN DEL MENSAJE
                # ==================================================

                await websocket.send_json({
                    "type": "done",
                })

            except httpx.HTTPError as e:

                print(
                    f"Error HTTP comunicándose "
                    f"con Ollama: {e}"
                )

                await websocket.send_json({
                    "type": "error",
                    "message": (
                        "No se pudo comunicar "
                        "con Ollama."
                    ),
                })

            except Exception as e:

                print(
                    f"Error procesando Ollama: {e}"
                )

                await websocket.send_json({
                    "type": "error",
                    "message": (
                        "Ocurrió un error "
                        "procesando la respuesta."
                    ),
                })

    except WebSocketDisconnect:

        print(
            "Cliente WebSocket desconectado."
        )

    except Exception as e:

        print(
            f"Error WebSocket: {e}"
        )

    finally:

        print(
            "Conexión WebSocket finalizada."
        )