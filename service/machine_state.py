"""
Máquina de estados finita para la conversación de Altea.

Este módulo es puro:
- No conoce WebSocket.
- No conoce Ollama.
- No conoce la base de datos.
- No conoce los slots de evaluación.

Solo sabe qué transiciones son válidas entre estados, dado un evento.
"""

from __future__ import annotations

from enum import Enum


# ==========================================================
# ESTADOS
# ==========================================================

class ConversationState(str, Enum):
    """
    Estados posibles de la conversación.

    IDLE:
        No hay evaluación activa. El usuario puede chatear libremente.

    EVALUATION:
        Evaluación activa. Se están recopilando slots.
        Puede haber slots llenos y otros pendientes.

    EVALUATING:
        Todos los slots requeridos están completos.
        El motor determinista está calculando el resultado.
        Este estado es transitorio: no debería durar más de un tick.

    COMPLETED:
        El resultado ya fue emitido al cliente.
        El usuario puede hacer preguntas sobre él o iniciar otra evaluación.
    """

    IDLE = "idle"
    EVALUATION = "evaluation"
    EVALUATING = "evaluating"
    COMPLETED = "completed"


# ==========================================================
# EVENTOS
# ==========================================================

class ConversationEvent(str, Enum):
    """
    Eventos que pueden disparar una transición.

    USER_TEXT:
        El usuario envió texto libre (puede contener un slot o no).

    USER_START_EVAL:
        El usuario pidió explícitamente iniciar una evaluación.

    SLOT_FILLED:
        Se extrajo y validó un slot de evaluación del texto del usuario.
        No implica que la evaluación esté completa.

    ALL_SLOTS_FILLED:
        Ya no faltan slots requeridos. Se puede calcular.

    ENGINE_DONE:
        El motor determinista terminó de calcular el resultado.

    USER_RESET:
        El usuario quiere reiniciar la conversación/evaluación.
    """

    USER_TEXT = "user_text"
    USER_START_EVAL = "user_start_eval"
    SLOT_FILLED = "slot_filled"
    ALL_SLOTS_FILLED = "all_slots_filled"
    ENGINE_DONE = "engine_done"
    USER_RESET = "user_reset"


# ==========================================================
# ERROR
# ==========================================================

class InvalidTransitionError(Exception):
    """
    Se lanza cuando se intenta aplicar un evento que no es válido
    desde el estado actual.

    El ConversationManager decide qué hacer con esto:
    - ignorarlo silenciosamente,
    - responder con un mensaje de error,
    - o registrar el incidente para depuración.
    """

    def __init__(
        self,
        state: ConversationState,
        event: ConversationEvent,
    ):
        self.state = state
        self.event = event

        super().__init__(
            f"Transición inválida: "
            f"evento '{event.value}' "
            f"no permitido desde estado '{state.value}'."
        )


# ==========================================================
# TABLA DE TRANSICIONES
# ==========================================================

# Estructura:
#   {
#       estado_actual: {
#           evento: estado_siguiente,
#           ...
#       },
#       ...
#   }
#
# Si un evento no aparece en el diccionario del estado actual,
# la transición es inválida.

TRANSITIONS: dict[ConversationState, dict[ConversationEvent, ConversationState]] = {

    ConversationState.IDLE: {
        ConversationEvent.USER_TEXT: ConversationState.IDLE,
        ConversationEvent.USER_START_EVAL: ConversationState.EVALUATION,
        ConversationEvent.USER_RESET: ConversationState.IDLE,
    },

    ConversationState.EVALUATION: {
        ConversationEvent.USER_TEXT: ConversationState.EVALUATION,
        ConversationEvent.SLOT_FILLED: ConversationState.EVALUATION,
        ConversationEvent.ALL_SLOTS_FILLED: ConversationState.EVALUATING,
        ConversationEvent.USER_START_EVAL: ConversationState.EVALUATION,
        ConversationEvent.USER_RESET: ConversationState.IDLE,
    },

    ConversationState.EVALUATING: {
        ConversationEvent.ENGINE_DONE: ConversationState.COMPLETED,
        ConversationEvent.USER_RESET: ConversationState.IDLE,
    },

    ConversationState.COMPLETED: {
        ConversationEvent.USER_TEXT: ConversationState.IDLE,
        ConversationEvent.USER_START_EVAL: ConversationState.EVALUATION,
        ConversationEvent.USER_RESET: ConversationState.IDLE,
    },
}


# ==========================================================
# MÁQUINA
# ==========================================================

class StateMachine:
    """
    Máquina de estados de la conversación.

    Uso:
        fsm = StateMachine()
        fsm.state                       # ConversationState.IDLE
        fsm.handle(ConversationEvent.USER_START_EVAL)
        fsm.state                       # ConversationState.EVALUATION

    La máquina NO guarda datos de slots, historial ni nada más.
    Solo el estado actual.
    """

    def __init__(
        self,
        initial: ConversationState = ConversationState.IDLE,
    ):
        self._state = initial

    # ------------------------------------------------------
    # Propiedad de solo lectura
    # ------------------------------------------------------

    @property
    def state(self) -> ConversationState:
        return self._state

    # ------------------------------------------------------
    # Aplicar evento
    # ------------------------------------------------------

    def handle(
        self,
        event: ConversationEvent,
    ) -> ConversationState:
        """
        Aplica un evento y devuelve el nuevo estado.

        Lanza InvalidTransitionError si el evento no es válido
        desde el estado actual.
        """

        allowed = TRANSITIONS.get(self._state, {})

        if event not in allowed:
            raise InvalidTransitionError(self._state, event)

        self._state = allowed[event]

        return self._state

    # ------------------------------------------------------
    # Consultar sin aplicar
    # ------------------------------------------------------

    def can_handle(
        self,
        event: ConversationEvent,
    ) -> bool:
        """
        Devuelve True si el evento es válido desde el estado actual,
        sin modificar el estado.
        """

        return event in TRANSITIONS.get(self._state, {})

    # ------------------------------------------------------
    # Reset
    # ------------------------------------------------------

    def reset(self) -> None:
        """
        Vuelve al estado inicial. Útil para reconexiones o tests.
        """

        self._state = ConversationState.IDLE

    # ------------------------------------------------------
    # Representación
    # ------------------------------------------------------

    def __repr__(self) -> str:
        return f"StateMachine(state={self._state.value!r})"