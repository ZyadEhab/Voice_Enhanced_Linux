"""Status events that every pipeline stage sends to the GUI.

Contract (PROJECT_CONTEXT.md, Section 9.2):  Event(stage, state, text)

Vocabulary the GUI understands
------------------------------
stage            state                                     text
---------------  ----------------------------------------  ---------------------------
"listening"      "ready" | "listening" | "processing" |    (optional note, unused)
                 "speaking" | "error"
"command"        language code: "en" | "ar"                recognized command text
"understanding"  "allowed" | "rejected" |                  intent name, e.g. LIST_FILES
                 "needs_confirmation"
"execution"      "awaiting_confirmation" | "running" |     (optional note)
                 "completed" | "rejected" | "failed" |
                 "cancelled"
"result"         "en" | "ar"  (language of the reply)      speakable result message
"error"          (anything)                                readable error message

The pipeline never touches Tkinter. It only calls emit(Event(...)); the GUI reads
the thread-safe queue with after(), because Tkinter is not thread-safe.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

# Mic / pipeline states shown in the state indicator.
STATES = ("ready", "listening", "processing", "speaking", "error")

# Execution statuses shown in the badge (key -> label).
EXECUTION_STATUSES = {
    "awaiting_confirmation": "Awaiting confirmation",
    "running": "Running",
    "completed": "Completed",
    "rejected": "Rejected",
    "failed": "Failed",
    "cancelled": "Cancelled",
}

# Statuses after which the command is finished and goes into the history.
TERMINAL_EXECUTION = {"completed", "rejected", "failed", "cancelled"}

CONFIRM_TIMEOUT_SECONDS = 10   # auto-cancel (PROJECT_CONTEXT.md, Section 11)


@dataclass(frozen=True)
class Event:
    stage: str
    state: str
    text: str = ""


# emit(event) is what the GUI hands to the pipeline.
Emit = Callable[[Event], None]
# confirm(prompt) -> bool blocks the pipeline thread until the user answers.
Confirm = Callable[[str], bool]
# A pipeline is any callable with this shape. main.py will provide the real one.
#   pipeline(emit, language, confirm) -> None      ("en" or "ar" = GUI language switch)
