"""Stand-in pipeline so the GUI works before the real modules exist.

Same shape as the real pipeline (see gui/events.py):
    pipeline(emit, language, confirm) -> None

It fakes every stage with short sleeps and cycles through demo commands for the
selected language: a normal command, a dangerous one (asks for confirmation) and
an unsupported one (rejected). main.py replaces this with the real pipeline.
"""
from __future__ import annotations

import itertools
import time

from .events import Confirm, Emit, Event

# (language, spoken text, intent, needs_confirmation, result message, confirm prompt)
DEMOS = [
    ("en", "Show my files", "LIST_FILES", False,
     "You have 2 folders and 3 files in your workspace.", ""),
    ("en", "Delete report", "DELETE_FILE", True,
     "The file report was deleted.", "Do you want to delete report?"),
    ("en", "What is the weather today", "UNKNOWN", False,
     "Sorry, I can't do that. Please give one of the supported commands.", ""),
    ("ar", "اعرض ملفاتي", "LIST_FILES", False,
     "لديك مجلدان وثلاثة ملفات في مساحة العمل.", ""),
    ("ar", "احذف report", "DELETE_FILE", True,
     "تم حذف الملف report.", "هل تريد حذف الملف report؟"),
    ("ar", "ما هو الطقس اليوم", "UNKNOWN", False,
     "عذرا، لا أستطيع تنفيذ هذا الأمر.", ""),
]

STEP_DELAY = 0.6   # seconds per fake stage


class StandInPipeline:
    def __init__(self, delay: float = STEP_DELAY):
        self._delay = delay
        self._cycles = {
            lang: itertools.cycle([d for d in DEMOS if d[0] == lang])
            for lang in ("en", "ar")
        }

    def __call__(self, emit: Emit, language: str, confirm: Confirm) -> None:
        lang = language if language in self._cycles else "en"
        _, text, intent, needs_confirm, message, prompt = next(self._cycles[lang])

        emit(Event("listening", "listening"))
        self._pause()
        emit(Event("listening", "processing"))
        emit(Event("command", lang, text))
        self._pause()

        if intent == "UNKNOWN":
            emit(Event("understanding", "rejected", intent))
            emit(Event("execution", "rejected"))
            emit(Event("result", lang, message))
            return

        if needs_confirm:
            emit(Event("understanding", "needs_confirmation", intent))
            emit(Event("execution", "awaiting_confirmation"))
            if not confirm(prompt):
                cancelled = "Cancelled." if lang == "en" else "تم الإلغاء."
                emit(Event("execution", "cancelled"))
                emit(Event("result", lang, cancelled))
                return
        else:
            emit(Event("understanding", "allowed", intent))

        emit(Event("execution", "running"))
        self._pause()
        emit(Event("execution", "completed"))
        emit(Event("result", lang, message))

    def _pause(self) -> None:
        if self._delay:
            time.sleep(self._delay)
