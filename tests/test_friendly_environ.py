from registered.friendly_environ import FriendlyEnviron
import pytest


def test_key_present():
    env = FriendlyEnviron({"KEY": "value"})
    assert env["KEY"] == "value"
    assert env.get("KEY", "missing") == "value"


def test_key_missing_get():
    env = FriendlyEnviron({})
    assert env.get("MISSING") == None
    assert env.get("MISSING", "missing") == "missing"


def test_key_not_str():
    env = FriendlyEnviron({})
    with pytest.raises(TypeError, match=r".*int"):
        env[1]

    with pytest.raises(TypeError, match=r".*int"):
        env.get(1)


def test_key_missing():
    env = FriendlyEnviron({})
    with pytest.raises(KeyError) as excinfo:
        env["MISSING"]

    assert ".env" in str(excinfo.value)
