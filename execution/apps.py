from __future__ import annotations
 
import os
import shutil
import subprocess
 
from execution.files import OperationResult
 
try:
    import psutil
except ImportError:  # keeps opening apps working if psutil is not installed
    psutil = None
 
CLOSE_TIMEOUT_SECONDS = 3
MAX_ECHO_LENGTH = 40  # do not read long unknown names back out loud
 
# The allow-list (Section 5.1 of PROJECT_CONTEXT.md).
#   command        -> the ONLY program that will be started
#   process_names  -> names psutil may report for it (Linux truncates names
#                     to 15 characters, so both forms are listed)
#   aliases        -> spoken names, English and Arabic
APPS = {
    "firefox": {
        "command": "firefox",
        "process_names": {"firefox", "firefox-bin"},
        "labels": {"en": "Firefox", "ar": "فايرفوكس"},
        "aliases": ["firefox", "browser", "web browser", "فايرفوكس",
                    "المتصفح", "متصفح"],
    },
    "terminal": {
        "command": "gnome-terminal",
        "process_names": {"gnome-terminal-server", "gnome-terminal-",
                          "gnome-terminal"},
        "labels": {"en": "Terminal", "ar": "التيرمينال"},
        "aliases": ["terminal", "gnome-terminal", "التيرمينال", "تيرمينال"],
    },
    "calculator": {
        "command": "gnome-calculator",
        "process_names": {"gnome-calculator", "gnome-calculato"},
        "labels": {"en": "Calculator", "ar": "الحاسبة"},
        "aliases": ["calculator", "gnome-calculator", "الحاسبة", "حاسبة", "الة حاسبة"],
    },
    "files": {
        "command": "nautilus",
        "process_names": {"nautilus"},
        "labels": {"en": "Files", "ar": "مدير الملفات"},
        "aliases": ["files", "file manager", "nautilus", "مدير الملفات"],
    },
    "editor": {
        "command": "gedit",
        "process_names": {"gedit"},
        "labels": {"en": "Text editor", "ar": "محرر النصوص"},
        "aliases": ["text editor", "editor", "gedit", "محرر النصوص",
                    "محرر نصوص"],
    },
}
 
_ALIAS_TO_KEY = {
    alias: key for key, app in APPS.items() for alias in app["aliases"]
}
 
MESSAGES = {
    "en": {
        "app_unknown": "{name} is not on the allowed applications list.",
        "app_missing": "{name} is not installed on this computer.",
        "app_opened": "{name} was opened.",
        "app_closed": "{name} was closed.",
        "app_not_running": "{name} is not running.",
        "failed": "The operation failed.",
    },
    "ar": {
        "app_unknown": "{name} غير موجود في قائمة التطبيقات المسموحة.",
        "app_missing": "{name} غير مثبت على هذا الجهاز.",
        "app_opened": "تم فتح {name}.",
        "app_closed": "تم إغلاق {name}.",
        "app_not_running": "{name} لا يعمل حاليا.",
        "failed": "فشلت العملية.",
    },
}
 
 
def _msg(language: str, key: str, **values) -> str:
    table = MESSAGES.get(language, MESSAGES["en"])
    return table[key].format(**values)
 
 
def _fail(language: str, key: str, **values) -> OperationResult:
    return OperationResult(False, _msg(language, key, **values), [])
 
 
def _label(key: str, language: str) -> str:
    labels = APPS[key]["labels"]
    return labels.get(language, labels["en"])
 
 
def resolve_app(name):
    """Turn a spoken name into an allow-list key, or None if not allowed."""
    if not isinstance(name, str):
        return None
    cleaned = " ".join(name.lower().split())
    return _ALIAS_TO_KEY.get(cleaned)
 
 
def _unknown(name, language: str) -> OperationResult:
    shown = str(name).strip()[:MAX_ECHO_LENGTH] if name is not None else ""
    return _fail(language, "app_unknown", name=shown or "?")
 
 
def _detach_options() -> dict:
    """Let the new app keep running on its own (POSIX only)."""
    return {"start_new_session": True} if os.name == "posix" else {}
 
 
# --------------------------------------------------------------------------
# Open
# --------------------------------------------------------------------------
def open_application(name, language: str = "en") -> OperationResult:
    """Start an allow-listed application as a new process."""
    key = resolve_app(name)
    if key is None:
        return _unknown(name, language)
 
    label = _label(key, language)
    command = APPS[key]["command"]
    if shutil.which(command) is None:
        return _fail(language, "app_missing", name=label)
 
    try:
        # Argument list, no Shell. Output is discarded so a noisy app cannot
        # flood our terminal.
        subprocess.Popen(
            [command],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **_detach_options(),
        )
    except OSError:
        return _fail(language, "failed")
    return OperationResult(True, _msg(language, "app_opened", name=label), [key])
 
 
# --------------------------------------------------------------------------
# Close
# --------------------------------------------------------------------------
def _protected_pids() -> set:
    """This program and its parents must never be closed (e.g. our terminal)."""
    pids = {os.getpid()}
    try:
        pids.update(parent.pid for parent in psutil.Process().parents())
    except Exception:
        pass
    return pids
 
 
def close_application(name, language: str = "en") -> OperationResult:
    """Close every running process of an allow-listed application."""
    key = resolve_app(name)
    if key is None:
        return _unknown(name, language)
    if psutil is None:
        return _fail(language, "failed")
 
    label = _label(key, language)
    wanted = APPS[key]["process_names"]
    protected = _protected_pids()
 
    try:
        matches = [
            proc for proc in psutil.process_iter(["pid", "name"])
            if (proc.info.get("name") or "") in wanted
            and proc.info.get("pid") not in protected
        ]
    except psutil.Error:
        return _fail(language, "failed")
 
    if not matches:
        return _fail(language, "app_not_running", name=label)
 
    stopped = []
    for proc in matches:
        try:
            proc.terminate()  # polite request first (SIGTERM)
            stopped.append(proc)
        except psutil.NoSuchProcess:
            pass  # already gone
        except psutil.AccessDenied:
            continue
 
    if not stopped:
        return _fail(language, "failed")
 
    _gone, still_alive = psutil.wait_procs(stopped, timeout=CLOSE_TIMEOUT_SECONDS)
    for proc in still_alive:
        try:
            proc.kill()  # last resort (SIGKILL)
        except psutil.Error:
            pass
 
    return OperationResult(True, _msg(language, "app_closed", name=label), [key])
 