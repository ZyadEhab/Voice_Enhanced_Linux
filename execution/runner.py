"""Execution hub: routes APPROVED intents. Never uses shell=True; arguments are lists."""
from dataclasses import dataclass

from execution.system_info import get_system_usage, get_running_processes
from validation.validator import validate
from execution.apps import open_application, close_application
from execution.files import (
    list_files, create_file, create_folder, rename_file, delete_file, OperationResult,
)


@dataclass
class ExecutionResult:
    success: bool
    message: str


def _map_result(op: OperationResult) -> ExecutionResult:
    return ExecutionResult(success=op.success, message=op.message)


def _first(params: dict, *keys):
    """First non-empty value among the accepted parameter names."""
    for k in keys:
        v = params.get(k)
        if v not in (None, ""):
            return v
    return None


def execute(intent_data: dict, confirmed: bool = False, language: str = None) -> ExecutionResult:
    """Re-validates (defence in depth). DELETE_FILE / CLOSE_APPLICATION run only if confirmed=True.

    `language` ("en"/"ar") selects the reply language; falls back to intent_data["language"], then "en".
    """
    check = validate(intent_data)
    if not check.allowed:
        return ExecutionResult(False, check.reason)
    if check.needs_confirmation and not confirmed:
        return ExecutionResult(False, "This action needs your confirmation first.")

    intent = intent_data["intent"]
    params = intent_data.get("params") or {}
    language = language or intent_data.get("language") or "en"

    # The NLP module emits params["name"]; file/folder/old_name are accepted aliases.
    name = _first(params, "name", "file", "folder", "old_name")
    new_name = _first(params, "new_name", "new")

    try:
        if intent == "SHOW_SYSTEM_USAGE":
            return ExecutionResult(True, get_system_usage(params.get("resource"), language))
        if intent == "SHOW_PROCESSES":
            return ExecutionResult(True, get_running_processes(language=language))
        if intent == "OPEN_APPLICATION":
            return _map_result(open_application(params.get("app"), language))
        if intent == "CLOSE_APPLICATION":
            return _map_result(close_application(params.get("app"), language))
        if intent == "LIST_FILES":
            return _map_result(list_files(language))
        if intent == "CREATE_FILE":
            return _map_result(create_file(name, language))
        if intent == "CREATE_FOLDER":
            return _map_result(create_folder(name, language))
        if intent == "RENAME_FILE":
            return _map_result(rename_file(name, new_name, language))
        if intent == "DELETE_FILE":
            return _map_result(delete_file(name, language))
        return ExecutionResult(False, "I do not know how to execute that command.")
    except Exception:
        return ExecutionResult(False, "The operation failed.")


if __name__ == "__main__":
    print(execute({"intent": "SHOW_SYSTEM_USAGE", "params": {"resource": "cpu"}}))
