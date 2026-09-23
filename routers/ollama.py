"""
Router WebSocket para el chatbot.

Este router es DELGADO. Solo:
- Acepta conexiones WebSocket.
- Parsea JSON entrante.
- Delega al ConversationManager.
- Envía eventos al cliente.
- Maneja desconexiones.

Toda la lógica de negocio vive en service/conversation/manager.py.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from database.ollama_config import OLLAMA_MODEL, OLLAMA_URL
from service.conversation.manager import ConversationManager
from service.llm import OllamaClient


router = APIRouter(
    prefix="/ollama",
    tags=["Ollama"],
)


# ==========================================================
# CLIENTE COMPARTIDO
# ==========================================================

# Un único cliente de Ollama para toda la app.
# No tiene estado mutable, se puede reutilizar sin problema.
_llm_client = OllamaClient(
    url=OLLAMA_URL,
    model=OLLAMA_MODEL,
)


# ==========================================================
# WEBSOCKET
# ==========================================================

@router.websocket("/ws")
async def ollama_websocket(websocket: WebSocket):
    await websocket.accept()
    print("Cliente WebSocket conectado.")

    # Un manager por conexión.
    manager = ConversationManager(llm=_llm_client)

    try:
        while True:
            # ----------------------------------------------
            # Recibir mensaje
            # ----------------------------------------------

            raw = await websocket.receive_text()

            # ----------------------------------------------
            # Parsear JSON
            # ----------------------------------------------

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "code": "invalid_message",
                    "message": "El mensaje no es JSON válido.",
                })
                await websocket.send_json({"type": "done"})
                continue

            # ----------------------------------------------
            # Validar tipo
            # ----------------------------------------------

            tipo = data.get("type")

            if not isinstance(tipo, str):
                await websocket.send_json({
                    "type": "error",
                    "code": "invalid_message",
                    "message": "Falta el campo 'type'.",
                })
                await websocket.send_json({"type": "done"})
                continue

            # ----------------------------------------------
            # Delegar al manager
            # ----------------------------------------------

            try:
                if tipo == "chat":
                    content = data.get("content", "")
                    if not isinstance(content, str):
                        content = ""

                    async for evento in manager.handle_chat(content):
                        await websocket.send_json(evento)

                elif tipo == "start_evaluation":
                    async for evento in manager.handle_start_evaluation():
                        await websocket.send_json(evento)

                elif tipo == "session_init":
                    user_id = data.get("user_id")
                    if user_id is not None and not isinstance(user_id, str):
                        user_id = None

                    async for evento in manager.handle_session_init(user_id):
                        await websocket.send_json(evento)

                else:
                    await websocket.send_json({
                        "type": "error",
                        "code": "invalid_message",
                        "message": f"Tipo de mensaje desconocido: '{tipo}'.",
                    })
                    await websocket.send_json({"type": "done"})

            except Exception as e:
                # Error inesperado procesando el turno.
                print(f"Error procesando turno: {e}")

                await websocket.send_json({
                    "type": "error",
                    "code": "internal_error",
                    "message": "Ocurrió un error procesando el mensaje.",
                })
                await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        print("Cliente WebSocket desconectado.")

    except Exception as e:
        print(f"Error WebSocket: {e}")

    finally:
        print("Conexión WebSocket finalizada.")