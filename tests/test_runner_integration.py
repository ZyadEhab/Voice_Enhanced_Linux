"""NLP -> validator -> runner contract tests (uses a temporary workspace)."""
import pytest
import execution.files as F
from execution import runner
from execution.apps import resolve_app
from nlp.intents import ALLOWED_APPS
from validation.validator import validate


@pytest.fixture(autouse=True)
def tmp_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "WORKSPACE", tmp_path / "ws")


def run(intent, confirmed=False, **params):
    lang = params.pop("language", None)
    return runner.execute({"intent": intent, "params": params}, confirmed, lang)


def test_every_nlp_app_value_is_accepted_everywhere():
    for command in set(ALLOWED_APPS.values()):
        assert validate({"intent": "OPEN_APPLICATION", "params": {"app": command}}).allowed
        assert resolve_app(command) is not None, command


def test_file_lifecycle_with_nlp_param_name():
    assert run("CREATE_FILE", name="notes").success
    assert run("CREATE_FOLDER", name="proj").success
    assert "notes.txt" in run("LIST_FILES").message
    assert run("RENAME_FILE", name="notes", new_name="report").success
    assert not run("DELETE_FILE", name="report").success          # needs confirmation
    assert run("DELETE_FILE", confirmed=True, name="report").success
    assert not run("DELETE_FILE", confirmed=True, name="report").success  # already gone


def test_traversal_blocked():
    assert not run("CREATE_FILE", name="../evil").success
    assert not run("DELETE_FILE", confirmed=True, name="../x").success


def test_arabic_reply_language():
    assert "مساحة" in run("LIST_FILES", language="ar").message
    assert "المعالج" in run("SHOW_SYSTEM_USAGE", resource="cpu", language="ar").message


def test_close_needs_confirmation():
    assert not run("CLOSE_APPLICATION", app="gnome-terminal").success
