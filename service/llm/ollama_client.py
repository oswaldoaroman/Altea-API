"""
Cliente para Ollama.

Wrapper limpio sobre httpx. Sin lógica de negocio.
Solo: dado un prompt y un system, devuelve texto.

Uso:
    client = OllamaClient(url=..., model=...)
    texto = await client.generate(prompt="...", system="...")
"""

from __future__ import annotations

import re

import httpx


# ==========================================================
# ERRORES
# ==========================================================

class OllamaError(Exception):
    """Error base de Ollama."""


class OllamaUnavailableError(OllamaError):
    """Ollama no está accesible (timeout, conexión rechazada, DNS)."""


class OllamaResponseError(OllamaError):
    """Ollama respondió con un error HTTP o JSON inválido."""


# ==========================================================
# LIMPIEZA DE RESPUESTA
# ==========================================================

# DeepSeek-R1 y otros modelos de razonamiento emiten bloques
# de "pensamiento" internos que el usuario no debe ver.
_THINK_PATTERN = re.compile(
    r"<think(?:ing)?>.*?</think(?:ing)?>",
    re.DOTALL | re.IGNORECASE,
)


def _limpiar_respuesta(texto: str) -> str:
    """Elimina bloques de razonamiento interno y espacios sobrantes."""
    texto = _THINK_PATTERN.sub("", texto)
    return texto.strip()


# ==========================================================
# CLIENTE
# ==========================================================

class OllamaClient:
    """
    Cliente de Ollama.

    Instanciar una vez y reutilizar. No tiene estado mutable.
    """

    def __init__(
        self,
        url: str,
        model: str,
        timeout: float = 60.0,
    ):
        self._url = url
        self._model = model
        self._timeout = timeout

    # ------------------------------------------------------
    # GENERATE
    # ------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        system: str,
    ) -> str:
        """
        Genera una respuesta del LLM.

        Devuelve solo el texto limpio.
        Lanza OllamaError si algo falla.
        """

        payload = {
            "model": self._model,
            "prompt": prompt,
            "system": system,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
            ) as client:
                response = await client.post(
                    self._url,
                    json=payload,
                )

        except httpx.TimeoutException as e:
            raise OllamaUnavailableError(
                f"Ollama no respondió en {self._timeout}s."
            ) from e

        except httpx.ConnectError as e:
            raise OllamaUnavailableError(
                "No se pudo conectar con Ollama."
            ) from e

        except httpx.HTTPError as e:
            raise OllamaUnavailableError(
                f"Error de red hablando con Ollama: {e}"
            ) from e

        # --------------------------------------------------
        # VALIDAR STATUS
        # --------------------------------------------------

        if response.status_code != 200:
            raise OllamaResponseError(
                f"Ollama devolvió status {response.status_code}: "
                f"{response.text[:200]}"
            )

        # --------------------------------------------------
        # PARSEAR JSON
        # --------------------------------------------------

        try:
            data = response.json()
        except ValueError as e:
            raise OllamaResponseError(
                f"Respuesta de Ollama no es JSON válido: {e}"
            ) from e

        # --------------------------------------------------
        # EXTRAER RESPUESTA
        # --------------------------------------------------

        texto = data.get("response")

        if not isinstance(texto, str):
            raise OllamaResponseError(
                "Respuesta de Ollama sin campo 'response' válido."
            )

        return _limpiar_respuesta(texto)

    # ------------------------------------------------------
    # IS_AVAILABLE
    # ------------------------------------------------------

    async def is_available(self) -> bool:
        """
        Comprueba si Ollama está accesible.

        Hace un POST con prompt vacío y timeout corto.
        Devuelve True si responde 200.
        """

        payload = {
            "model": self._model,
            "prompt": "",
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.post(
                    self._url,
                    json=payload,
                )
                return response.status_code == 200

        except httpx.HTTPError:
            return False