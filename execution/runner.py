"""Execution hub: routes APPROVED intents. Never uses shell=True; arguments are lists."""
import os
import shutil
import subprocess
from dataclasses import dataclass

import psutil

from execution.system_info import get_system_usage, get_running_processes
from validation.validator import validate

# from execution.files import run_file_intent   # enable when the file module is merged

# App command -> process names to look for when closing. VERIFY with `ps -e` on the demo
# machine (e.g. Ubuntu's Firefox is a snap; gnome-terminal runs as gnome-terminal-server).
PROCESS_NAMES = {
    "firefox": {"firefox", "firefox-bin"},
    "gnome-terminal": {"gnome-terminal-server"},
    "gnome-calculator": {"gnome-calculator", "gnome-calculato"},
    "nautilus": {"nautilus"},
    "gedit": {"gedit"},
}


@dataclass
class ExecutionResult:
    success: bool
    message: str


def _open_app(app: str) -> ExecutionResult:
    if shutil.which(app) is None:
        return ExecutionResult(False, f"{app} is not installed on this system.")
    subprocess.Popen([app], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    return ExecutionResult(True, f"The application {app} has been opened.")


def _close_app(app: str) -> ExecutionResult:
    # Never close our own process tree (e.g. the terminal this program was started from).
    protected = {os.getpid()} | {p.pid for p in psutil.Process().parents()}
    targets = []
    for p in psutil.process_iter(["name", "pid"]):
        if p.info["name"] in PROCESS_NAMES.get(app, {app}) and p.info["pid"] not in protected:
            targets.append(p)
    if not targets:
        return ExecutionResult(False, f"{app} is not running.")
    for p in targets:
        try:
            p.terminate()
        except psutil.Error:
            pass
    psutil.wait_procs(targets, timeout=3)
    return ExecutionResult(True, f"The application {app} has been closed.")


def execute(intent_data: dict, confirmed: bool = False) -> ExecutionResult:
    """Re-validates (defence in depth). Dangerous intents run only if confirmed=True."""
    check = validate(intent_data)
    if not check.allowed:
        return ExecutionResult(False, check.reason)
    if check.needs_confirmation and not confirmed:
        return ExecutionResult(False, "This action needs your confirmation first.")

    intent = intent_data["intent"]
    params = intent_data.get("params") or {}
    try:
        if intent == "SHOW_SYSTEM_USAGE":
            return ExecutionResult(True, get_system_usage(params["resource"]))
        if intent == "SHOW_PROCESSES":
            return ExecutionResult(True, get_running_processes())
        if intent == "OPEN_APPLICATION":
            return _open_app(params["app"])
        if intent == "CLOSE_APPLICATION":
            return _close_app(params["app"])
        # File intents: placeholder until the file management module is merged
        return ExecutionResult(False, "File operations are waiting for the file management module.")
    except Exception:
        return ExecutionResult(False, "The operation failed.")


if __name__ == "__main__":
    print(execute({"intent": "SHOW_SYSTEM_USAGE", "params": {"resource": "cpu"}}))
