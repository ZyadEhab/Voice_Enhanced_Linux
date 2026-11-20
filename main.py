"""
Voice-Enhanced Linux - Main Pipeline Controller (main.py)
Owner: Role 1 - Team Leader & Linux System Environment (Zyad Ehab)

Wires all team modules together, pre-warms AI models into RAM,
updates the GUI status bar, and launches the Tkinter application:
Microphone -> STT -> NLP -> Validation -> Execution -> TTS & GUI
"""

import queue
import time
from pathlib import Path
from typing import Optional

from execution.runner import execute
from gui.events import Confirm, Emit, Event
from nlp.understanding import understand, warmup as warmup_nlp
from stt.interface import transcribe
from stt.recorder import record
from stt.transcriber import _get_model as warmup_stt
from tts.speaker import speak
from validation.validator import validate

# Ensure safe working folder exists with owner-only permissions (0700 / drwx------)
SAFE_WORKSPACE = Path.home() / "VoiceLinuxWorkspace"


def init_safe_workspace() -> Path:
    SAFE_WORKSPACE.mkdir(parents=True, exist_ok=True)
    SAFE_WORKSPACE.chmod(0o700)
    return SAFE_WORKSPACE


def prewarm_models() -> None:
    """Pre-loads faster-whisper and sentence-transformers into RAM before demo starts."""
    print("[System] Pre-warming AI models into RAM for instant response...")
    t0 = time.time()
    try:
        warmup_nlp()
        print("  -> [NLP] sentence-transformers model loaded in RAM.")
    except Exception as e:
        print(f"  -> [NLP] Warm-up note: {e}")

    try:
        warmup_stt()
        print("  -> [STT] faster-whisper (small) model loaded in RAM.")
    except Exception as e:
        print(f"  -> [STT] Warm-up note: {e}")

    print(f"[System] All models pre-warmed and ready in {time.time() - t0:.1f}s!")


def _build_confirm_prompt(intent_data: dict, language: str) -> str:
    intent_name = intent_data.get("intent", "")
    params = intent_data.get("params") or {}
    target = (
        params.get("name")
        or params.get("file")
        or params.get("folder")
        or params.get("path")
        or params.get("app")
        or params.get("application")
        or ""
    )
    if language == "ar":
        if intent_name == "DELETE_FILE":
            return f"هل تريد حذف {target}؟" if target else "هل أنت متأكد من الحذف؟"
        if intent_name == "CLOSE_APPLICATION":
            return f"هل تريد إغلاق {target}؟" if target else "هل أنت متأكد من إغلاق التطبيق؟"
        return f"هل تؤكد تنفيذ {intent_name}؟"
    else:
        if intent_name == "DELETE_FILE":
            return f"Do you want to delete {target}?" if target else "Confirm delete operation?"
        if intent_name == "CLOSE_APPLICATION":
            return f"Do you want to close {target}?" if target else "Confirm closing application?"
        return f"Do you want to run {intent_name}?"


class VoicePipelineController:
    """Main pipeline controller connecting all team modules to the GUI."""

    def __init__(self, event_queue: Optional[queue.Queue] = None, gui_callback=None):
        self.event_queue = event_queue or queue.Queue()
        self.gui_callback = gui_callback
        self.voice_reply_enabled = True
        init_safe_workspace()

    def __call__(self, emit: Emit, language: str, confirm: Confirm) -> None:
        """Called directly by gui.app.App in a background worker thread."""
        lang = language if language in ("en", "ar") else "en"
        try:
            # Stage 1: Microphone capture
            emit(Event("listening", "listening", "Listening for command..."))
            audio = record()
            if audio is None or len(audio) == 0:
                msg = (
                    "لم يتم التقاط صوت. حاول مرة أخرى."
                    if lang == "ar"
                    else "No speech detected. Please try again."
                )
                emit(Event("error", "no_speech", msg))
                return

            # Stage 2: Speech-to-Text
            emit(Event("listening", "processing", "Transcribing speech..."))
            text, detected_lang = transcribe(audio, language=lang)
            text = (text or "").strip(" .!?,؟،")
            active_lang = detected_lang if detected_lang in ("en", "ar") else lang

            if not text:
                msg = (
                    "لم أتمكن من التعرف على الكلام. يرجى الإعادة."
                    if active_lang == "ar"
                    else "Could not recognize speech. Please repeat."
                )
                emit(Event("error", "unrecognized", msg))
                return

            emit(Event("command", active_lang, text))

            # Stage 3: Command Understanding (NLP)
            intent_data = understand(text, active_lang)
            intent_name = intent_data.get("intent", "UNKNOWN")

            # Stage 4: Command Validation
            val_res = validate(intent_data)
            if not val_res.allowed:
                emit(Event("understanding", "rejected", intent_name))
                emit(Event("execution", "rejected", val_res.reason))
                # validator.py returns English reasons, so speak them in English
                emit(Event("result", "en", val_res.reason))
                return

            if val_res.needs_confirmation:
                emit(Event("understanding", "needs_confirmation", intent_name))
                emit(Event("execution", "awaiting_confirmation", intent_name))
                prompt = _build_confirm_prompt(intent_data, active_lang)
                approved = confirm(prompt) if confirm is not None else False
                if not approved:
                    cancel_msg = (
                        "تم إلغاء العملية."
                        if active_lang == "ar"
                        else "Operation cancelled by user."
                    )
                    emit(Event("execution", "cancelled", cancel_msg))
                    emit(Event("result", active_lang, cancel_msg))
                    return
                emit(Event("understanding", "allowed", intent_name))
            else:
                emit(Event("understanding", "allowed", intent_name))

            # Stage 5: Linux Operation Execution
            emit(Event("execution", "running", intent_name))
            exec_res = execute(intent_data, confirmed=True, language=active_lang)
            exec_state = "completed" if exec_res.success else "failed"
            emit(Event("execution", exec_state, exec_res.message))

            # Stage 6: Result & Voice Reply
            emit(Event("result", active_lang, exec_res.message))

        except Exception as err:
            err_msg = f"Pipeline error: {err}"
            emit(Event("error", "exception", err_msg))


if __name__ == "__main__":
    print("=== Voice-Enhanced Linux Main Pipeline ===")
    ws = init_safe_workspace()
    print(f"[System] Safe workspace ready at: {ws} (mode {oct(ws.stat().st_mode & 0o777)})")

    # Pre-warm AI models into RAM so the first voice command responds instantly
    prewarm_models()

    import tkinter as tk
    from gui.app import App

    controller = VoicePipelineController()
    root = tk.Tk()
    app = App(root, pipeline=controller, speak_fn=speak, workspace=str(ws))

    # Update status bar to display real speech model instead of 'stand-in'
    app.set_info(model="faster-whisper (small)")

    root.mainloop()
