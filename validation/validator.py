"""Validation layer: the security gatekeeper between understanding and execution.

Rules (from the project spec):
  * only known intents, apps and resources are allowed (fixed allow-lists)
  * DELETE_FILE and CLOSE_APPLICATION need user confirmation
  * file/folder names can never leave ~/VoiceLinuxWorkspace
  * fail closed: anything missing, malformed or unexpected is rejected
"""
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationResult:
    allowed: bool
    needs_confirmation: bool
    reason: str


ALLOWED_INTENTS = {
    "LIST_FILES", "CREATE_FILE", "CREATE_FOLDER", "RENAME_FILE",
    "DELETE_FILE", "OPEN_APPLICATION", "CLOSE_APPLICATION",
    "SHOW_PROCESSES", "SHOW_SYSTEM_USAGE",
}
CONFIRM_INTENTS = {"DELETE_FILE", "CLOSE_APPLICATION"}
FILE_INTENTS = {"CREATE_FILE", "CREATE_FOLDER", "RENAME_FILE", "DELETE_FILE"}

ALLOWED_APPS = {"firefox", "gnome-terminal", "gnome-calculator", "nautilus", "gedit"}
ALLOWED_RESOURCES = {"ram", "cpu", "disk"}

WORKSPACE = Path.home() / "VoiceLinuxWorkspace"
MAX_NAME_LENGTH = 100

# Parameter keys. MUST match what nlp/understanding.py outputs (see context file).
NAME_KEYS = ("name", "file", "folder")
NEW_NAME_KEYS = ("new_name", "new")


def _first(params: dict, keys):
    for k in keys:
        v = params.get(k)
        if v not in (None, ""):
            return v
    return None


def _name_problem(value):
    """Return a reason string if the name is unsafe, else None."""
    if not isinstance(value, str) or not value.strip():
        return "The name is empty or invalid."
    if value in {".", ".."}:
        return "That name is not allowed."
    if "/" in value or "\\" in value or "\x00" in value:
        return "Invalid characters in name. Path traversal blocked."
    if len(value) > MAX_NAME_LENGTH:
        return "The name is too long."
    return None


def _reject(reason: str) -> ValidationResult:
    return ValidationResult(False, False, reason)


def validate(intent_data: dict) -> ValidationResult:
    if not isinstance(intent_data, dict):
        return _reject("Invalid command.")
    intent = intent_data.get("intent")
    params = intent_data.get("params") or {}
    if not isinstance(params, dict):
        return _reject("Invalid command parameters.")

    # 1. Unknown intents (also guards against non-string / unhashable values)
    if not isinstance(intent, str) or intent not in ALLOWED_INTENTS:
        return _reject("Intent not allowed or recognized.")

    # 2. Parameters the NLP layer reported as missing
    missing = intent_data.get("missing") or []
    if missing:
        return _reject("Missing information: " + ", ".join(map(str, missing)) + ".")

    # 3. Applications
    if intent in {"OPEN_APPLICATION", "CLOSE_APPLICATION"}:
        app = params.get("app")
        if not isinstance(app, str) or app not in ALLOWED_APPS:
            return _reject("Application is not on the safe list.")

    # 4. System resources
    if intent == "SHOW_SYSTEM_USAGE":
        res = params.get("resource")
        if not isinstance(res, str) or res not in ALLOWED_RESOURCES:
            return _reject("System resource not recognized.")

    # 5. Files: required names present, and EVERY string param is a safe name
    if intent in FILE_INTENTS:
        if _first(params, NAME_KEYS) is None:
            return _reject("Missing information: name.")
        if intent == "RENAME_FILE" and _first(params, NEW_NAME_KEYS) is None:
            return _reject("Missing information: new name.")
        for value in params.values():
            problem = _name_problem(value)
            if problem:
                return _reject(problem)

    return ValidationResult(True, intent in CONFIRM_INTENTS, "Allowed")


if __name__ == "__main__":
    print(validate({"intent": "DELETE_FILE", "params": {"name": "report.txt"}}))
