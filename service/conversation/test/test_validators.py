from service.conversation.validators import validar_dato


def test_validar_edad_ok():
    ok, value, error = validar_dato("edad", 30)
    assert ok is True
    assert value == 30
    assert error is None


def test_validar_edad_negativa():
    ok, _, error = validar_dato("edad", -5)
    assert ok is False
    assert error is not None


def test_validar_edad_demasiado_alta():
    ok, _, error = validar_dato("edad", 150)
    assert ok is False
    assert "120" in error


def test_validar_edad_decimal_rechazada():
    ok, _, error = validar_dato("edad", 30.5)
    assert ok is False