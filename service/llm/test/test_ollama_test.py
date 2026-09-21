"""
Tests del OllamaClient.

Usa httpx.MockTransport para simular respuestas de Ollama
sin necesidad de tener Ollama corriendo.
"""

import httpx
import pytest

from service.llm.ollama_client import (
    OllamaClient,
    OllamaResponseError,
    OllamaUnavailableError,
    _limpiar_respuesta,
)


# ==========================================================
# HELPERS
# ==========================================================

URL_FAKE = "http://fake-ollama.local/api/generate"
MODEL_FAKE = "fake-model"


def _client_con_handler(handler):
    """Crea un cliente cuyo httpx usa un transport mockeado."""

    transport = httpx.MockTransport(handler)

    # Inyectamos un AsyncClient ya configurado en el módulo.
    # Hack: sobreescribimos httpx.AsyncClient por un lambda que
    # siempre devuelve un cliente con el transport mockeado.
    original = httpx.AsyncClient

    def _factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    httpx.AsyncClient = _factory

    return OllamaClient(url=URL_FAKE, model=MODEL_FAKE)


@pytest.fixture(autouse=True)
def restaurar_httpx():
    original = httpx.AsyncClient
    yield
    httpx.AsyncClient = original


# ==========================================================
# LIMPIEZA
# ==========================================================

# Construimos las etiquetas por concatenación para evitar que
# cualquier editor o copia-pega se coma los `<...>`.

_OPEN_THINK = "<" + "think" + ">"
_CLOSE_THINK = "<" + "/" + "think" + ">"

_OPEN_THINKING = "<" + "thinking" + ">"
_CLOSE_THINKING = "<" + "/" + "thinking" + ">"


def test_limpiar_respuesta_sin_tags():
    assert _limpiar_respuesta("Hola mundo") == "Hola mundo"


def test_limpiar_respuesta_con_think():
    texto = f"{_OPEN_THINK}pensar cosas{_CLOSE_THINK} Hola"
    assert _limpiar_respuesta(texto) == "Hola"


def test_limpiar_respuesta_con_thinking():
    texto = f"{_OPEN_THINKING}razonando{_CLOSE_THINKING} Hola"
    assert _limpiar_respuesta(texto) == "Hola"


def test_limpiar_respuesta_multilinea():
    texto = f"{_OPEN_THINK}paso 1\npaso 2{_CLOSE_THINK}\n\nHola"
    assert _limpiar_respuesta(texto) == "Hola"


# ==========================================================
# GENERATE — CASO FELIZ
# ==========================================================

@pytest.mark.asyncio
async def test_generate_ok():
    def handler(request):
        return httpx.Response(
            200,
            json={"response": "Hola, soy Altea."},
        )

    client = _client_con_handler(handler)

    texto = await client.generate(prompt="hola", system="eres altea")

    assert texto == "Hola, soy Altea."


@pytest.mark.asyncio
async def test_generate_limpia_think():
    def handler(request):
        return httpx.Response(
            200,
            json={"response": " razonando  Hola"},
        )

    client = _client_con_handler(handler)

    texto = await client.generate(prompt="hola", system="")

    assert texto == "Hola"


# ==========================================================
# GENERATE — ERRORES
# ==========================================================

@pytest.mark.asyncio
async def test_generate_http_error():
    def handler(request):
        return httpx.Response(500, text="Internal Server Error")

    client = _client_con_handler(handler)

    with pytest.raises(OllamaResponseError):
        await client.generate(prompt="hola", system="")


@pytest.mark.asyncio
async def test_generate_json_invalido():
    def handler(request):
        return httpx.Response(200, text="no es json")

    client = _client_con_handler(handler)

    with pytest.raises(OllamaResponseError):
        await client.generate(prompt="hola", system="")


@pytest.mark.asyncio
async def test_generate_sin_campo_response():
    def handler(request):
        return httpx.Response(200, json={"otro": "campo"})

    client = _client_con_handler(handler)

    with pytest.raises(OllamaResponseError):
        await client.generate(prompt="hola", system="")


@pytest.mark.asyncio
async def test_generate_timeout():
    def handler(request):
        raise httpx.TimeoutException("timeout simulado")

    client = _client_con_handler(handler)

    with pytest.raises(OllamaUnavailableError):
        await client.generate(prompt="hola", system="")


@pytest.mark.asyncio
async def test_generate_connect_error():
    def handler(request):
        raise httpx.ConnectError("conexión rechazada")

    client = _client_con_handler(handler)

    with pytest.raises(OllamaUnavailableError):
        await client.generate(prompt="hola", system="")


# ==========================================================
# IS_AVAILABLE
# ==========================================================

@pytest.mark.asyncio
async def test_is_available_true():
    def handler(request):
        return httpx.Response(200, json={"response": ""})

    client = _client_con_handler(handler)

    assert await client.is_available() is True


@pytest.mark.asyncio
async def test_is_available_false_por_error():
    def handler(request):
        raise httpx.ConnectError("no")

    client = _client_con_handler(handler)

    assert await client.is_available() is False


@pytest.mark.asyncio
async def test_is_available_false_por_status():
    def handler(request):
        return httpx.Response(500)

    client = _client_con_handler(handler)

    assert await client.is_available() is False


@pytest.mark.asyncio
async def test_generate_limpia_think():
    contenido = f"{_OPEN_THINK}razonando{_CLOSE_THINK} Hola"

    def handler(request):
        return httpx.Response(
            200,
            json={"response": contenido},
        )

    client = _client_con_handler(handler)

    texto = await client.generate(prompt="hola", system="")

    assert texto == "Hola"