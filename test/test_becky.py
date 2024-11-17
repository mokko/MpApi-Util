from MpApi.Utils.becky.set_fields_Object import (
    _is_space_etc,
    _is_int,
)
import pytest


def test_is_space_etc() -> None:
    assert _is_space_etc(None) is True
    assert _is_space_etc("") is True
    assert _is_space_etc(" ") is True
    assert _is_space_etc(" c") is False
    with pytest.raises(TypeError):
        _is_space_etc(1)


def test_is_int() -> None:
    assert _is_int(1) is True
    assert _is_int(None) is False
    with pytest.raises(TypeError):
        _is_int("1")
