"""
ConversationManager — el orquestador del chatbot.

Recibe mensajes del cliente, actualiza el estado, consulta la FSM,
extrae slots, llama al motor cuando corresponde y produce una
secuencia de eventos para enviar al cliente.

REGLA DE ORO:
- Este módulo NO habla con WebSocket.
- NO habla con httpx directamente.
- NO usa FastAPI.
- Recibe un OllamaClient en el constructor.
- Devuelve un AsyncIterator[dict] de eventos.

Los eventos que emite coinciden exactamente con el protocolo WS
definido en el diseño.

IMPORTANTE:
- Las preguntas de evaluación son PREDEFINIDAS.
- El LLM NO se usa para generar preguntas de slots.
- El LLM solo se usa para chat libre.
"""

from __future__ import annotations

import re
from typing import Any, AsyncIterator

from service.machine_state import (
    ConversationEvent,
    ConversationState,
    InvalidTransitionError,
    StateMachine,
)

from service.evaluation.engine import evaluar
from service.evaluation.models import EvaluationInput

from .fallbacks import (
    categoria_colesterol,
    categoria_glucosa,
    convertir_presion,
    parsear_categoria,
)
from .prompts import (
    SYSTEM_PROMPT_BASE,
    prompt_chat,
)
from .slots import extraer_slots
from .validators import CAMPOS_REQUERIDOS, validar_dato


# ==========================================================
# CONSTANTES
# ==========================================================

# Orden en el que se piden los campos.
ORDEN_CAMPOS = [
    "peso",
    "altura",
    "edad",
    "presionSistolica",
    "presionDiastolica",
    "fuma",
    "consumeAlcohol",
    "actividadFisica",
    "glucosa",
    "colesterol",
]

# Máximo de reintentos por campo antes de usar fallback.
MAX_REINTENTOS = 2


# ==========================================================
# PATRONES
# ==========================================================

_NO_SE_PATTERNS = [
    re.compile(r"\bno\s+s[eé]\b", re.IGNORECASE),
    re.compile(r"\bno\s+me\s+acuerdo\b", re.IGNORECASE),
    re.compile(r"\bno\s+recuerdo\b", re.IGNORECASE),
    re.compile(r"\bno\s+la\s+tengo\b", re.IGNORECASE),
    re.compile(r"\bno\s+lo\s+tengo\b", re.IGNORECASE),
    re.compile(r"\bno\s+tengo\s+ese\s+dato\b", re.IGNORECASE),
    re.compile(r"\bni\s+idea\b", re.IGNORECASE),
]

_INTENCION_EVALUACION = [
    re.compile(r"\bquiero\s+evaluar(me)?\b", re.IGNORECASE),
    re.compile(r"\bquiero\s+saber\s+mi\s+riesgo\b", re.IGNORECASE),
    re.compile(r"\bquiero\s+hacer\s+(una\s+)?evaluaci[oó]n\b", re.IGNORECASE),
    re.compile(r"\bempecemos\b", re.IGNORECASE),
    re.compile(r"\bcomenzar\s+(la\s+)?evaluaci[oó]n\b", re.IGNORECASE),
    re.compile(r"\bquiero\s+conocer\s+mi\s+riesgo\b", re.IGNORECASE),
]


# ==========================================================
# PREGUNTAS PREDEFINIDAS
# ==========================================================

PREGUNTAS_PREDEFINIDAS: dict[str, str] = {
    "peso": "¿Cuál es tu peso en kilogramos?",
    "altura": "¿Cuál es tu altura? Puedes decirme en centímetros o metros.",
    "edad": "¿Cuántos años tienes?",
    "presionSistolica": (
        "¿Conoces tu presión arterial? Puedes decirme algo como "
        "'130 sobre 85'. Si no la sabes, dime 'no sé'."
    ),
    "presionDiastolica": (
        "¿Y el segundo valor de tu presión? Por ejemplo, si tu presión "
        "es 130 sobre 85, el segundo valor es 85."
    ),
    "fuma": "¿Fumas actualmente?",
    "consumeAlcohol": "¿Consumes alcohol?",
    "actividadFisica": (
        "¿Haces actividad física? Puedes responder 'activo', "
        "'moderado' o 'sedentario'."
    ),
    "glucosa": (
        "¿Conoces tu nivel de glucosa en sangre? Si no, dime 'no sé'."
    ),
    "colesterol": (
        "¿Conoces tu nivel de colesterol? Si no, dime 'no sé'."
    ),
}


PREGUNTAS_CATEGORIA: dict[str, str] = {
    "presionSistolica": (
        "No hay problema. ¿Crees que tu presión arterial es baja, "
        "normal o alta?"
    ),
    "presionDiastolica": (
        "No hay problema. ¿Crees que tu presión arterial es baja, "
        "normal o alta?"
    ),
    "glucosa": (
        "No hay problema. ¿Crees que tu glucosa está normal, "
        "elevada o alta?"
    ),
    "colesterol": (
        "No hay problema. ¿Crees que tu colesterol está normal, "
        "elevado o alto?"
    ),
}


# ==========================================================
# MANAGER
# ==========================================================

class ConversationManager:
    """
    Orquesta el flujo conversacional.

    Uso:
        manager = ConversationManager(llm=client)
        async for evento in manager.handle_chat("hola"):
            await ws.send_json(evento)
    """

    def __init__(self, llm: Any):
        self.llm = llm
        self.fsm = StateMachine()
        self.slots: dict[str, Any] = {}
        self.historial: list[dict] = []
        self.reintentos: dict[str, int] = {}
        self.user_id: str | None = None
        self._inicializar_slots()

    # ======================================================
    # API PÚBLICA
    # ======================================================

    async def handle_session_init(
        self,
        user_id: str | None,
    ) -> AsyncIterator[dict]:
        """
        Inicializa la sesión con un user_id (opcional).
        En v1 no se persiste; solo se guarda.
        """
        self.user_id = user_id
        yield {"type": "done"}

    async def handle_start_evaluation(self) -> AsyncIterator[dict]:
        """
        Inicia una evaluación explícitamente.
        """
        async for evento in self._iniciar_evaluacion():
            yield evento

    async def handle_chat(self, content: str) -> AsyncIterator[dict]:
        """
        Procesa un mensaje de chat del usuario.

        Decide, según el estado actual:
        - Si está en EVALUATION, intenta extraer slots.
        - Si no, responde con chat libre.
        - Si detecta intención de evaluar, inicia evaluación.
        """
        if not content or not content.strip():
            yield {
                "type": "error",
                "code": "invalid_message",
                "message": "El mensaje no puede estar vacío.",
            }
            yield {"type": "done"}
            return

        content = content.strip()
        self.historial.append({"role": "usuario", "content": content})

        # En evaluación: procesar como posible slot.
        if self.fsm.state == ConversationState.EVALUATION:
            async for evento in self._procesar_mensaje_evaluacion(content):
                yield evento
            return

        # En COMPLETED: volver a IDLE.
        if self.fsm.state == ConversationState.COMPLETED:
            try:
                self.fsm.handle(ConversationEvent.USER_TEXT)
            except InvalidTransitionError:
                pass

        # Detectar intención de evaluación.
        if self._detectar_intencion_evaluacion(content):
            async for evento in self._iniciar_evaluacion():
                yield evento
            return

        # Chat libre.
        async for evento in self._chat_libre(content):
            yield evento

    # ======================================================
    # INICIALIZACIÓN DE SLOTS
    # ======================================================

    def _inicializar_slots(self) -> None:
        self.slots = {campo: None for campo in CAMPOS_REQUERIDOS}
        self.reintentos = {campo: 0 for campo in CAMPOS_REQUERIDOS}

    # ======================================================
    # INICIAR EVALUACIÓN
    # ======================================================

    async def _iniciar_evaluacion(self) -> AsyncIterator[dict]:
        try:
            self.fsm.handle(ConversationEvent.USER_START_EVAL)
        except InvalidTransitionError:
            self.fsm.reset()
            self.fsm.handle(ConversationEvent.USER_START_EVAL)

        self._inicializar_slots()

        yield {
            "type": "evaluation_started",
            "required_fields": list(CAMPOS_REQUERIDOS),
        }

        async for evento in self._preguntar_siguiente_campo():
            yield evento

        yield {"type": "done"}

    # ======================================================
    # PROCESAR MENSAJE EN EVALUACIÓN
    # ======================================================

    async def _procesar_mensaje_evaluacion(
        self,
        content: str,
    ) -> AsyncIterator[dict]:
        campo_pendiente = self._siguiente_campo()

        # 1. Detectar "no sé".
        if self._detectar_no_se(content) and campo_pendiente:
            async for evento in self._manejar_no_se(campo_pendiente):
                yield evento
            return

        # 2. Extraer slots.
        slots_extraidos = self._extraer_y_validar(content)

        if not slots_extraidos:
            # Puede ser una respuesta de categoría.
            if campo_pendiente in (
                "presionSistolica",
                "presionDiastolica",
                "glucosa",
                "colesterol",
            ):
                async for evento in self._intentar_parsear_categoria(
                    content, campo_pendiente
                ):
                    yield evento
                return

            # Ni slot ni categoría. Reintentar.
            async for evento in self._reintentar_o_fallback(campo_pendiente):
                yield evento
            return

        # 3. Aplicar slots.
        for field, value in slots_extraidos:
            self.slots[field] = value
            self.reintentos[field] = 0

        for field, value in slots_extraidos:
            yield {
                "type": "evaluation_data",
                "field": field,
                "value": value,
                "progress": self._contar_llenos(),
                "total": len(CAMPOS_REQUERIDOS),
            }

        # 4. ¿Completa?
        if self._evaluacion_completa():
            async for evento in self._finalizar_evaluacion():
                yield evento
            return

        # 5. Preguntar siguiente.
        async for evento in self._preguntar_siguiente_campo():
            yield evento

        yield {"type": "done"}

    # ======================================================
    # MANEJO DE "NO SÉ"
    # ======================================================

    async def _manejar_no_se(self, campo: str) -> AsyncIterator[dict]:
        """
        El usuario dijo "no sé" para un campo.

        - Si el campo tiene categoría (presión, glucosa, colesterol),
          se le pregunta por categoría.
        - Si no, se aplica el fallback sintético directo.
        """

        if campo in PREGUNTAS_CATEGORIA:
            texto = PREGUNTAS_CATEGORIA[campo]

            self.historial.append({"role": "altea", "content": texto})

            yield {"type": "assistant_message", "content": texto}
            yield {"type": "done"}
            return

        # Campos sin categoría: fallback directo.
        async for evento in self._aplicar_fallback(campo):
            yield evento

    # ======================================================
    # INTENTAR PARSEAR CATEGORÍA
    # ======================================================

    async def _intentar_parsear_categoria(
        self,
        content: str,
        campo_pendiente: str,
    ) -> AsyncIterator[dict]:
        categoria = None

        if campo_pendiente in ("presionSistolica", "presionDiastolica"):
            categoria = parsear_categoria(content, "presion")
        elif campo_pendiente == "glucosa":
            categoria = parsear_categoria(content, "glucosa")
        elif campo_pendiente == "colesterol":
            categoria = parsear_categoria(content, "colesterol")

        if categoria is None:
            async for evento in self._reintentar_o_fallback(campo_pendiente):
                yield evento
            return

        # Presión: ambos valores a la vez.
        if campo_pendiente in ("presionSistolica", "presionDiastolica"):
            async for evento in self._aplicar_fallback_presion(categoria):
                yield evento
            return

        # Glucosa / colesterol.
        if campo_pendiente == "glucosa":
            self.slots["glucosa"] = float(categoria)
            self.reintentos["glucosa"] = 0
            yield {
                "type": "evaluation_data",
                "field": "glucosa",
                "value": float(categoria),
                "progress": self._contar_llenos(),
                "total": len(CAMPOS_REQUERIDOS),
            }
        elif campo_pendiente == "colesterol":
            self.slots["colesterol"] = float(categoria)
            self.reintentos["colesterol"] = 0
            yield {
                "type": "evaluation_data",
                "field": "colesterol",
                "value": float(categoria),
                "progress": self._contar_llenos(),
                "total": len(CAMPOS_REQUERIDOS),
            }

        if self._evaluacion_completa():
            async for evento in self._finalizar_evaluacion():
                yield evento
            return

        async for evento in self._preguntar_siguiente_campo():
            yield evento

        yield {"type": "done"}

    # ======================================================
    # APLICAR FALLBACK
    # ======================================================

    async def _aplicar_fallback(
        self,
        campo: str,
    ) -> AsyncIterator[dict]:
        # Presión: caso especial.
        if campo in ("presionSistolica", "presionDiastolica"):
            async for evento in self._aplicar_fallback_presion(2):
                yield evento
            return

        # Glucosa / colesterol: default categoría 2 (elevado).
        if campo == "glucosa":
            self.slots["glucosa"] = 2.0
            yield {
                "type": "evaluation_data",
                "field": "glucosa",
                "value": 2.0,
                "progress": self._contar_llenos(),
                "total": len(CAMPOS_REQUERIDOS),
            }
        elif campo == "colesterol":
            self.slots["colesterol"] = 2.0
            yield {
                "type": "evaluation_data",
                "field": "colesterol",
                "value": 2.0,
                "progress": self._contar_llenos(),
                "total": len(CAMPOS_REQUERIDOS),
            }
        elif campo == "edad":
            self.slots["edad"] = 30
            yield {
                "type": "evaluation_data",
                "field": "edad",
                "value": 30,
                "progress": self._contar_llenos(),
                "total": len(CAMPOS_REQUERIDOS),
            }
        else:
            # Otros campos: valor genérico para no bloquear.
            # (peso, altura, fuma, consumeAlcohol, actividadFisica)
            defaults = {
                "peso": 70.0,
                "altura": 170.0,
                "fuma": False,
                "consumeAlcohol": False,
                "actividadFisica": 1,
            }
            if campo in defaults:
                self.slots[campo] = defaults[campo]
                yield {
                    "type": "evaluation_data",
                    "field": campo,
                    "value": defaults[campo],
                    "progress": self._contar_llenos(),
                    "total": len(CAMPOS_REQUERIDOS),
                }

        if self._evaluacion_completa():
            async for evento in self._finalizar_evaluacion():
                yield evento
            return

        async for evento in self._preguntar_siguiente_campo():
            yield evento

        yield {"type": "done"}

    async def _aplicar_fallback_presion(
        self,
        categoria: int,
    ) -> AsyncIterator[dict]:
        edad = self.slots.get("edad") or 30
        peso = self.slots.get("peso") or 70.0

        sistolica, diastolica = convertir_presion(categoria, edad, peso)

        self.slots["presionSistolica"] = sistolica
        self.slots["presionDiastolica"] = diastolica

        yield {
            "type": "evaluation_data",
            "field": "presionSistolica",
            "value": sistolica,
            "progress": self._contar_llenos(),
            "total": len(CAMPOS_REQUERIDOS),
        }
        yield {
            "type": "evaluation_data",
            "field": "presionDiastolica",
            "value": diastolica,
            "progress": self._contar_llenos(),
            "total": len(CAMPOS_REQUERIDOS),
        }

        if self._evaluacion_completa():
            async for evento in self._finalizar_evaluacion():
                yield evento
            return

        async for evento in self._preguntar_siguiente_campo():
            yield evento

        yield {"type": "done"}

    # ======================================================
    # REINTENTAR O FALLBACK
    # ======================================================

    async def _reintentar_o_fallback(
        self,
        campo: str | None,
    ) -> AsyncIterator[dict]:
        if campo is None:
            async for evento in self._preguntar_siguiente_campo():
                yield evento
            yield {"type": "done"}
            return

        self.reintentos[campo] = self.reintentos.get(campo, 0) + 1

        if self.reintentos[campo] > MAX_REINTENTOS:
            async for evento in self._aplicar_fallback(campo):
                yield evento
            return

        # Repetir pregunta del mismo campo (predefinida, sin LLM).
        texto = self._preguntar_campo(campo)

        self.historial.append({"role": "altea", "content": texto})

        yield {"type": "assistant_message", "content": texto}
        yield {"type": "done"}

    # ======================================================
    # FINALIZAR EVALUACIÓN
    # ======================================================

    async def _finalizar_evaluacion(self) -> AsyncIterator[dict]:
        try:
            self.fsm.handle(ConversationEvent.ALL_SLOTS_FILLED)
        except InvalidTransitionError:
            pass

        try:
            inp = self._construir_input()
        except Exception as e:
            yield {
                "type": "error",
                "code": "internal_error",
                "message": f"No se pudo construir el input: {e}",
            }
            yield {"type": "done"}
            return

        edad = float(self.slots.get("edad") or 30)

        result = evaluar(inp, edad)

        try:
            self.fsm.handle(ConversationEvent.ENGINE_DONE)
        except InvalidTransitionError:
            pass

        yield {
            "type": "evaluation_complete",
            "result": result.to_dict(),
            "input": inp.to_dict(),
        }

        yield {"type": "done"}

    # ======================================================
    # PREGUNTAR SIGUIENTE CAMPO
    # ======================================================

    async def _preguntar_siguiente_campo(self) -> AsyncIterator[dict]:
        campo = self._siguiente_campo()

        if campo is None:
            return

        texto = self._preguntar_campo(campo)

        self.historial.append({"role": "altea", "content": texto})

        yield {"type": "assistant_message", "content": texto}

    # ======================================================
    # CHAT LIBRE
    # ======================================================

    async def _chat_libre(self, content: str) -> AsyncIterator[dict]:
        try:
            self.fsm.handle(ConversationEvent.USER_TEXT)
        except InvalidTransitionError:
            pass

        try:
            texto = await self._llm_chat_libre(content)
        except Exception as e:
            yield {
                "type": "error",
                "code": "llm_unavailable",
                "message": str(e),
            }
            yield {"type": "done"}
            return

        self.historial.append({"role": "altea", "content": texto})

        yield {"type": "assistant_message", "content": texto}
        yield {"type": "done"}

    # ======================================================
    # PREGUNTA PREDEFINIDA
    # ======================================================

    def _preguntar_campo(self, campo: str) -> str:
        """
        Devuelve la pregunta predefinida para un campo.

        No llama al LLM. Las preguntas de evaluación son cerradas
        y siempre las mismas.
        """
        return PREGUNTAS_PREDEFINIDAS.get(
            campo,
            f"¿Cuál es tu {campo}?",
        )

    # ======================================================
    # LLAMADAS AL LLM
    # ======================================================

    async def _llm_chat_libre(self, content: str) -> str:
        prompt = prompt_chat(mensaje=content, historial=self.historial)
        return await self.llm.generate(prompt, SYSTEM_PROMPT_BASE)

    # ======================================================
    # HELPERS
    # ======================================================

    def _evaluacion_completa(self) -> bool:
        return all(
            self.slots.get(campo) is not None
            for campo in CAMPOS_REQUERIDOS
        )

    def _contar_llenos(self) -> int:
        return sum(1 for v in self.slots.values() if v is not None)

    def _siguiente_campo(self) -> str | None:
        for campo in ORDEN_CAMPOS:
            if self.slots.get(campo) is None:
                return campo
        return None

    def _detectar_no_se(self, texto: str) -> bool:
        return any(p.search(texto) for p in _NO_SE_PATTERNS)

    def _detectar_intencion_evaluacion(self, texto: str) -> bool:
        return any(p.search(texto) for p in _INTENCION_EVALUACION)

    def _extraer_y_validar(
        self,
        texto: str,
    ) -> list[tuple[str, Any]]:
        crudos = extraer_slots(texto)
        resultado: list[tuple[str, Any]] = []

        for field, value in crudos:
            ok, valor, _ = validar_dato(field, value)
            if ok:
                resultado.append((field, valor))

        return resultado

    def _construir_input(self) -> EvaluationInput:
        ap_hi = self.slots.get("presionSistolica")
        ap_lo = self.slots.get("presionDiastolica")

        if ap_hi is None or ap_lo is None:
            edad = self.slots.get("edad") or 30
            peso = self.slots.get("peso") or 70.0
            ap_hi, ap_lo = convertir_presion(2, edad, peso)

        gluc_raw = self.slots.get("glucosa") or 100.0
        chol_raw = self.slots.get("colesterol") or 180.0

        gluc = self._normalizar_categoria(gluc_raw, "glucosa")
        chol = self._normalizar_categoria(chol_raw, "colesterol")

        return EvaluationInput(
            ap_hi=float(ap_hi),
            ap_lo=float(ap_lo),
            weight=float(self.slots.get("peso") or 70.0),
            height=float(self.slots.get("altura") or 170.0),
            cholesterol=chol,
            gluc=gluc,
            smoke=1.0 if self.slots.get("fuma") else 0.0,
            alco=1.0 if self.slots.get("consumeAlcohol") else 0.0,
            active=float(self.slots.get("actividadFisica") or 1),
        )

    def _normalizar_categoria(
        self,
        valor: float,
        campo: str,
    ) -> float:
        if 1.0 <= valor <= 3.0:
            return float(valor)

        if campo == "glucosa":
            return categoria_glucosa(valor)

        if campo == "colesterol":
            return categoria_colesterol(valor)

        return valor