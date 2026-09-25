import pytest

# These two helpers were removed from set_fields_Object during the sanitization
# refactor (64026c1), so this module currently tests nothing that exists. Skip
# rather than let the ImportError abort collection of the whole suite — the
# module needs rewriting against whatever replaced them, or deleting.
try:
    from MpApi.Utils.becky.set_fields_Object import (
        _is_space_etc,
        _is_int,
    )
except ImportError as exc:  # pragma: no cover
    pytest.skip(f"helpers under test no longer exist: {exc}", allow_module_level=True)


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
