"""
Script temporal para probar el WebSocket del backend.

Uso:
    python scripts/test_ws.py
"""

import asyncio
import json

import websockets


URL = "ws://127.0.0.1:8000/ollama/ws"


async def enviar(ws, mensaje):
    print(f">>> {mensaje}")
    await ws.send(json.dumps(mensaje))


async def recibir(ws):
    print("Esperando respuesta...\n")
    while True:
        raw = await ws.recv()
        data = json.loads(raw)
        print(f"<<< {data}")
        if data.get("type") == "done":
            print()
            break


async def main():
    async with websockets.connect(URL) as ws:
        print("Conectado.\n")

        # ------------------------------------------
        # Prueba 1: chat libre
        # ------------------------------------------

        await enviar(ws, {"type": "chat", "content": "Hola Altea"})
        await recibir(ws)

        # ------------------------------------------
        # Prueba 2: iniciar evaluación
        # ------------------------------------------

        await enviar(ws, {"type": "start_evaluation"})
        await recibir(ws)

        # ------------------------------------------
        # Prueba 3: dar un par de datos
        # ------------------------------------------

        await enviar(ws, {"type": "chat", "content": "peso 76"})
        await recibir(ws)

        await enviar(ws, {"type": "chat", "content": "mido 175"})
        await recibir(ws)


if __name__ == "__main__":
    asyncio.run(main())