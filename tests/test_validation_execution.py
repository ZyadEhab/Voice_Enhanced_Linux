import pytest
from validation.validator import validate
from execution import runner


def intent(kind, **params):
    return {"intent": kind, "params": params}


@pytest.mark.parametrize("name", ["LIST_FILES", "SHOW_PROCESSES"])
def test_simple_allowed(name):
    r = validate(intent(name))
    assert r.allowed and not r.needs_confirmation


@pytest.mark.parametrize("data", [
    intent("DELETE_FILE", name="a.txt"), intent("CLOSE_APPLICATION", app="firefox")])
def test_confirmation_required(data):
    r = validate(data)
    assert r.allowed and r.needs_confirmation


@pytest.mark.parametrize("data", [
    intent("UNKNOWN"), intent("SHUTDOWN"), {"intent": None}, {}, None, "rm -rf /",
    {"intent": ["LIST_FILES"]}, {"intent": "LIST_FILES", "params": "x"},
    intent("OPEN_APPLICATION", app="rm"), intent("OPEN_APPLICATION"),
    intent("OPEN_APPLICATION", app=["firefox"]),
    intent("SHOW_SYSTEM_USAGE", resource="gpu"), intent("SHOW_SYSTEM_USAGE"),
])
def test_rejected(data):
    assert not validate(data).allowed


@pytest.mark.parametrize("bad", ["../secret", "a/b", "a\\b", "..", ".", "", "   ", "x" * 101, "a\x00b"])
@pytest.mark.parametrize("key", ["name", "file", "folder"])
def test_bad_file_names(bad, key):
    assert not validate(intent("CREATE_FILE", **{key: bad})).allowed


def test_arabic_name_ok_and_missing_name_rejected():
    assert validate(intent("CREATE_FILE", name="ملاحظات")).allowed
    assert not validate(intent("CREATE_FILE")).allowed


def test_rename_needs_both_and_checks_both():
    assert validate(intent("RENAME_FILE", name="a", new_name="b")).allowed
    assert not validate(intent("RENAME_FILE", name="a")).allowed
    assert not validate(intent("RENAME_FILE", name="a", new_name="../b")).allowed


def test_missing_from_nlp_rejected():
    d = intent("CREATE_FILE", name=None)
    d["missing"] = ["name"]
    assert not validate(d).allowed


def test_runner_refuses_unconfirmed_dangerous():
    assert not runner.execute(intent("CLOSE_APPLICATION", app="firefox")).success
    assert not runner.execute(intent("DELETE_FILE", name="a")).success










def test_system_info():
    for res in ("cpu", "ram", "disk"):
        assert runner.execute(intent("SHOW_SYSTEM_USAGE", resource=res)).success
    assert runner.execute(intent("SHOW_PROCESSES")).success


def test_runner_rejects_invalid_before_routing():
    r = runner.execute(intent("OPEN_APPLICATION", app="bash; rm -rf /"))
    assert not r.success
