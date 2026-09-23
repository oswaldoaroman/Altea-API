"""
Script para probar el flujo completo de evaluación end-to-end.
"""

import asyncio
import json

import websockets


URL = "ws://127.0.0.1:8000/ollama/ws"


async def enviar(ws, mensaje):
    print(f">>> {mensaje}")
    await ws.send(json.dumps(mensaje))


async def recibir(ws):
    print("Esperando...\n")
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

        # Iniciar evaluación.
        await enviar(ws, {"type": "start_evaluation"})
        await recibir(ws)

        # Enviar los 10 campos en orden.
        datos = [
            "peso 76",
            "mido 175",
            "tengo 40 años",
            "presión 130 sobre 85",
            "no fumo",
            "no tomo alcohol",
            "hago ejercicio regularmente",
            "mi glucosa es 100",
            "mi colesterol es 200",
        ]

        for dato in datos:
            await enviar(ws, {"type": "chat", "content": dato})
            await recibir(ws)


if __name__ == "__main__":
    asyncio.run(main())