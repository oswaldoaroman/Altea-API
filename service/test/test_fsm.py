"""
Tests de la máquina de estados de la conversación.

Sin dependencias externas. Se ejecutan con:

    pytest altea-api/conversation/tests/test_fsm.py -v
"""
import pytest

from service.machine_state import (
    ConversationEvent,
    ConversationState,
    InvalidTransitionError,
    StateMachine,
)


# ==========================================================
# Estado inicial
# ==========================================================

def test_estado_inicial_es_idle():
    fsm = StateMachine()
    assert fsm.state == ConversationState.IDLE


def test_estado_inicial_personalizado():
    fsm = StateMachine(initial=ConversationState.COMPLETED)
    assert fsm.state == ConversationState.COMPLETED


# ==========================================================
# Transiciones válidas — flujo feliz
# ==========================================================

def test_idle_a_evaluation_al_pedir_evaluacion():
    fsm = StateMachine()
    fsm.handle(ConversationEvent.USER_START_EVAL)
    assert fsm.state == ConversationState.EVALUATION


def test_evaluation_a_evaluating_al_completar_slots():
    fsm = StateMachine(initial=ConversationState.EVALUATION)
    fsm.handle(ConversationEvent.ALL_SLOTS_FILLED)
    assert fsm.state == ConversationState.EVALUATING


def test_evaluating_a_completed_al_terminar_engine():
    fsm = StateMachine(initial=ConversationState.EVALUATING)
    fsm.handle(ConversationEvent.ENGINE_DONE)
    assert fsm.state == ConversationState.COMPLETED


def test_flujo_completo():
    fsm = StateMachine()

    fsm.handle(ConversationEvent.USER_START_EVAL)
    assert fsm.state == ConversationState.EVALUATION

    fsm.handle(ConversationEvent.SLOT_FILLED)
    assert fsm.state == ConversationState.EVALUATION

    fsm.handle(ConversationEvent.ALL_SLOTS_FILLED)
    assert fsm.state == ConversationState.EVALUATING

    fsm.handle(ConversationEvent.ENGINE_DONE)
    assert fsm.state == ConversationState.COMPLETED


# ==========================================================
# Bucles válidos
# ==========================================================

def test_user_text_en_idle_se_queda_en_idle():
    fsm = StateMachine()
    fsm.handle(ConversationEvent.USER_TEXT)
    assert fsm.state == ConversationState.IDLE


def test_slot_filled_en_evaluation_se_queda_en_evaluation():
    fsm = StateMachine(initial=ConversationState.EVALUATION)
    fsm.handle(ConversationEvent.SLOT_FILLED)
    assert fsm.state == ConversationState.EVALUATION


def test_user_text_desde_completed_vuelve_a_idle():
    fsm = StateMachine(initial=ConversationState.COMPLETED)
    fsm.handle(ConversationEvent.USER_TEXT)
    assert fsm.state == ConversationState.IDLE


# ==========================================================
# Reset
# ==========================================================

def test_user_reset_desde_cualquier_estado():
    for estado in ConversationState:
        fsm = StateMachine(initial=estado)
        fsm.handle(ConversationEvent.USER_RESET)
        assert fsm.state == ConversationState.IDLE


# ==========================================================
# Transiciones inválidas
# ==========================================================

def test_no_se_puede_completar_slots_desde_idle():
    fsm = StateMachine()
    with pytest.raises(InvalidTransitionError):
        fsm.handle(ConversationEvent.ALL_SLOTS_FILLED)


def test_no_se_puede_terminar_engine_desde_idle():
    fsm = StateMachine()
    with pytest.raises(InvalidTransitionError):
        fsm.handle(ConversationEvent.ENGINE_DONE)


def test_no_se_puede_iniciar_evaluacion_desde_evaluating():
    fsm = StateMachine(initial=ConversationState.EVALUATING)
    with pytest.raises(InvalidTransitionError):
        fsm.handle(ConversationEvent.USER_START_EVAL)


def test_no_se_puede_recibir_slots_desde_completed():
    fsm = StateMachine(initial=ConversationState.COMPLETED)
    with pytest.raises(InvalidTransitionError):
        fsm.handle(ConversationEvent.SLOT_FILLED)


# ==========================================================
# can_handle no muta el estado
# ==========================================================

def test_can_handle_no_muta_estado():
    fsm = StateMachine()

    assert fsm.can_handle(ConversationEvent.USER_START_EVAL) is True
    assert fsm.state == ConversationState.IDLE

    assert fsm.can_handle(ConversationEvent.ENGINE_DONE) is False
    assert fsm.state == ConversationState.IDLE


# ==========================================================
# Reset de la máquina
# ==========================================================

def test_reset_vuelve_a_idle():
    fsm = StateMachine(initial=ConversationState.EVALUATING)
    fsm.reset()
    assert fsm.state == ConversationState.IDLE


# ==========================================================
# Error contiene información útil
# ==========================================================

def test_error_contiene_estado_y_evento():
    fsm = StateMachine(initial=ConversationState.IDLE)

    try:
        fsm.handle(ConversationEvent.ENGINE_DONE)
    except InvalidTransitionError as e:
        assert e.state == ConversationState.IDLE
        assert e.event == ConversationEvent.ENGINE_DONE
        assert "engine_done" in str(e)
        assert "idle" in str(e)
    else:
        pytest.fail("Se esperaba InvalidTransitionError")