"""
Voice-Enhanced Linux - Main Pipeline Controller (main.py)
Owner: Role 1 - Team Leader & Linux System Environment (Zyad Ehab)

Wires the agreed pipeline interfaces together:
Microphone -> transcribe(audio) -> understand(text, language)
           -> validate(intent) -> execute(intent) -> speak(message, language)
Communicates with the Tkinter GUI through a thread-safe queue.
Includes stand-in fallbacks so the pipeline runs before all teammate branches are merged.
"""

import os
import queue
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Any

# Ensure safe working folder exists with owner-only permissions (0700 / drwx------)
SAFE_WORKSPACE = Path.home() / "VoiceLinuxWorkspace"

def init_safe_workspace() -> Path:
    SAFE_WORKSPACE.mkdir(parents=True, exist_ok=True)
    SAFE_WORKSPACE.chmod(0o700)
    return SAFE_WORKSPACE

# --- Shared Data Structures (Section 5.2 / Section 9) ---
@dataclass
class ValidationResult:
    allowed: bool
    needs_confirmation: bool = False
    reason: str = ""

@dataclass
class ExecutionResult:
    success: bool
    message: str
    items: List[Any] = field(default_factory=list)

# --- Dynamic Module Imports with Stand-In Fallbacks (Section 12) ---
try:
    from stt.recorder import record
    from stt.transcriber import transcribe
except ImportError:
    def record():
        return b"stand_in_audio"
    def transcribe(audio):
        return "show my files", "en"

try:
    from nlp.understanding import understand
except ImportError:
    def understand(text: str, language: str = "en") -> dict:
        return {
            "text": text,
            "intent": "LIST_FILES",
            "params": {},
            "language": language,
            "confidence": 0.90,
            "method": "stand-in",
            "needs_confirmation": False,
            "missing": []
        }

try:
    from validation.validator import validate
except ImportError:
    def validate(intent: dict) -> ValidationResult:
        if intent.get("intent") == "UNKNOWN":
            return ValidationResult(False, False, "Unsupported command.")
        return ValidationResult(True, bool(intent.get("needs_confirmation", False)), "Allowed")

try:
    from execution.runner import execute
except ImportError:
    def execute(intent: dict) -> ExecutionResult:
        ws = init_safe_workspace()
        return ExecutionResult(True, f"Stand-in executed {intent.get('intent')} in {ws.name}.")

try:
    from tts.speaker import speak
except ImportError:
    def speak(message: str, language: str = "en"):
        print(f"[TTS ({language})]: {message}")


class VoicePipelineController:
    """Main loop orchestrating all pipeline stages on a background worker thread."""

    def __init__(self, event_queue: queue.Queue = None, gui_callback=None):
        self.event_queue = event_queue or queue.Queue()
        self.gui_callback = gui_callback
        self.voice_reply_enabled = True
        init_safe_workspace()

    def emit_event(self, stage: str, state: str, text: str = "", **extra):
        """Send status events to the GUI through a thread-safe queue (Section 5)."""
        event = {"stage": stage, "state": state, "text": text, "data": extra}
        self.event_queue.put(event)
        if self.gui_callback is not None:
            self.gui_callback(event)

    def start_voice_cycle(self, confirm_fn=None):
        """Run a single voice command cycle in a background thread so GUI never blocks."""
        worker = threading.Thread(
            target=self.run_pipeline_once,
            args=(confirm_fn,),
            daemon=True
        )
        worker.start()
        return worker

    def run_pipeline_once(self, confirm_fn=None) -> ExecutionResult:
        try:
            # Stage 1: Microphone capture
            self.emit_event("stt", "Listening", "Listening for command...")
            audio = record()
            if audio is None or len(audio) == 0:
                msg = "No speech detected. Please try again."
                self.emit_event("stt", "Error", msg)
                return ExecutionResult(False, msg)

            # Stage 2: Speech-to-Text
            self.emit_event("stt", "Processing", "Transcribing speech...")
            text, language = transcribe(audio)
            if not text:
                msg = "Could not recognize speech. Please repeat."
                self.emit_event("stt", "Error", msg)
                return ExecutionResult(False, msg)

            self.emit_event("command", "Completed", text, language=language)

            # Stage 3: Command Understanding (NLP)
            intent_data = understand(text, language)
            intent_name = intent_data.get("intent", "UNKNOWN")
            self.emit_event("understanding", "Completed", intent_name, intent=intent_data)

            # Stage 4: Command Validation
            val_res = validate(intent_data)
            if not val_res.allowed:
                self.emit_event("execution", "Rejected", val_res.reason)
                if self.voice_reply_enabled:
                    speak(val_res.reason, language)
                self.emit_event("stt", "Ready", "Ready")
                return ExecutionResult(False, val_res.reason)

            # Confirmation gate for dangerous commands (DELETE_FILE / CLOSE_APPLICATION)
            if val_res.needs_confirmation:
                self.emit_event("execution", "Awaiting confirmation", f"Confirm {intent_name}?")
                approved = confirm_fn(intent_data) if confirm_fn is not None else False
                if not approved:
                    cancel_msg = "Operation cancelled by user."
                    self.emit_event("execution", "Cancelled", cancel_msg)
                    if self.voice_reply_enabled:
                        speak(cancel_msg, language)
                    self.emit_event("stt", "Ready", "Ready")
                    return ExecutionResult(False, cancel_msg)

            # Stage 5: Linux Operation Execution
            self.emit_event("execution", "Running", f"Executing {intent_name}...")
            exec_res = execute(intent_data)
            exec_state = "Completed" if exec_res.success else "Failed"
            self.emit_event("execution", exec_state, exec_res.message)

            # Stage 6: Text-to-Speech Reply
            if self.voice_reply_enabled and exec_res.message:
                self.emit_event("stt", "Speaking", exec_res.message)
                speak(exec_res.message, language)

            self.emit_event("stt", "Ready", "Ready")
            return exec_res

        except Exception as err:
            err_msg = f"Pipeline error: {err}"
            self.emit_event("stt", "Error", err_msg)
            return ExecutionResult(False, err_msg)


if __name__ == "__main__":
    print("=== Voice-Enhanced Linux Main Pipeline ===")
    ws = init_safe_workspace()
    print(f"[System] Safe workspace ready at: {ws} (mode {oct(ws.stat().st_mode & 0o777)})")

    try:
        import tkinter as tk
        from gui.app import VoiceLinuxGUI
        root = tk.Tk()
        gui = VoiceLinuxGUI(root)
        controller = VoicePipelineController(gui_callback=gui.on_event)
        gui.controller = controller
        root.mainloop()
    except ImportError:
        print("[System] GUI module not merged yet. Running single pipeline verification cycle...")
        controller = VoicePipelineController()
        result = controller.run_pipeline_once()
        print(f"[Result] Success={result.success} | Message='{result.message}'")
