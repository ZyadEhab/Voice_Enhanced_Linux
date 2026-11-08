"""Voice-Enhanced Linux: Tkinter GUI.

Week 2: window skeleton following the Week 1 layout (PROJECT_CONTEXT.md, Section 11).
Week 3: espeak-ng spoken replies, recognized command + result display, and
        background threads so the window never freezes.

Run the demo with stand-in modules:   python -m gui.app

Thread model (OS concept: threads)
----------------------------------
main thread   Tkinter only. Reads the thread-safe queue with after() every 50 ms.
pipeline      One worker thread per Listen press. It runs the pipeline and only
thread        talks to the GUI by putting Events on the queue.
tts thread    One daemon thread that speaks replies one after another, so the
              blocking espeak-ng call never touches the main thread.

Security (Section 7, rule 7): the GUI only displays and triggers. Validation and
confirmation rules live in the validation layer; the GUI just asks the user and
returns yes/no. Nothing typed or spoken is ever run as a shell command here.
"""
from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from typing import Callable, Optional

from tts import speaker

from .arabic import shape
from .events import (
    CONFIRM_TIMEOUT_SECONDS,
    EXECUTION_STATUSES,
    TERMINAL_EXECUTION,
    Confirm,
    Emit,
    Event,
)
from .standins import StandInPipeline

# Theme: blue / white, matching the reports (Section 17).
NAVY = "#1F3864"
BLUE = "#2F5496"
LIGHT = "#F2F5FB"
WHITE = "#FFFFFF"

STATE_COLORS = {
    "ready": "#2E7D32",
    "listening": "#C62828",
    "processing": "#EF6C00",
    "speaking": BLUE,
    "error": "#B71C1C",
}
STATUS_COLORS = {
    "awaiting_confirmation": "#EF6C00",
    "running": "#EF6C00",
    "completed": "#2E7D32",
    "rejected": "#C62828",
    "failed": "#B71C1C",
    "cancelled": "#616161",
}
UNDERSTANDING_LABELS = {
    "allowed": "Allowed",
    "rejected": "Rejected",
    "needs_confirmation": "Needs confirmation",
}
POLL_MS = 50
_DONE = object()          # pipeline thread finished
_STOP_TTS = object()      # tells the tts thread to exit


class _ConfirmRequest:
    """Passed from the pipeline thread to the GUI thread; the pipeline waits on it."""

    def __init__(self, prompt: str, language: str):
        self.prompt = prompt
        self.language = language
        self.answer = False
        self.done = threading.Event()


class App:
    def __init__(
        self,
        root: tk.Tk,
        pipeline: Optional[Callable[[Emit, str, Confirm], None]] = None,
        speak_fn: Callable[[str, str], bool] = speaker.speak,
        workspace: str = "~/VoiceLinuxWorkspace",
    ):
        self.root = root
        self.pipeline = pipeline or StandInPipeline()
        self._speak = speak_fn
        self._queue: "queue.Queue[object]" = queue.Queue()
        self._tts_queue: "queue.Queue[object]" = queue.Queue()
        self._busy = False
        self._closing = False
        self._voice_on = True        # plain bool: safe to read from worker threads
        self._current = {"command": "", "intent": ""}
        self._confirm_win: Optional[tk.Toplevel] = None

        self.lang_var = tk.StringVar(value="en")
        self.voice_var = tk.BooleanVar(value=True)

        self._configure_window()
        self._build_header()
        self._build_body()
        self._build_status_bar(workspace)

        self.set_state("ready")
        self.set_execution(None)

        threading.Thread(target=self._tts_loop, daemon=True).start()
        self.root.after(POLL_MS, self._poll_queue)

    # ------------------------------------------------------------------ layout
    def _configure_window(self) -> None:
        self.root.title("Voice-Enhanced Linux")
        self.root.geometry("1000x680")
        self.root.minsize(900, 600)
        self.root.configure(bg=LIGHT)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=LIGHT)
        style.configure("TLabelframe", background=LIGHT)
        style.configure("TLabelframe.Label", background=LIGHT, foreground=NAVY,
                        font=("Arial", 10, "bold"))
        style.configure("TRadiobutton", background=LIGHT, font=("Arial", 10))
        style.configure("TCheckbutton", background=LIGHT, font=("Arial", 10))
        style.configure("Listen.TButton", font=("Arial", 12, "bold"), padding=8)
        style.configure("Treeview.Heading", background=NAVY, foreground=WHITE,
                        font=("Arial", 10, "bold"))
        style.configure("Treeview", rowheight=24, font=("Arial", 10))

    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg=NAVY)
        header.pack(fill="x")

        tk.Label(header, text="Voice-Enhanced Linux", bg=NAVY, fg=WHITE,
                 font=("Arial", 16, "bold")).pack(side="left", padx=16, pady=10)

        # 1. Listening state: button + state indicator
        self.state_label = tk.Label(header, text="", width=14, fg=WHITE,
                                    font=("Arial", 11, "bold"), pady=4)
        self.state_label.pack(side="right", padx=16, pady=10)
        self.listen_btn = ttk.Button(header, text="🎤  Listen", style="Listen.TButton",
                                     command=self.start_listening)
        self.listen_btn.pack(side="right", padx=4, pady=10)

        # Controls: EN / AR switch, voice reply on/off
        controls = tk.Frame(header, bg=NAVY)
        controls.pack(side="right", padx=16)
        ttk.Radiobutton(controls, text="EN", value="en", variable=self.lang_var).pack(side="left")
        ttk.Radiobutton(controls, text="AR", value="ar", variable=self.lang_var).pack(side="left")
        ttk.Checkbutton(controls, text="Voice reply", variable=self.voice_var,
                        command=self._on_voice_toggle).pack(side="left", padx=(12, 0))

    def _build_body(self) -> None:
        body = ttk.Frame(self.root, padding=12)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(3, weight=1)
        body.rowconfigure(4, weight=2)

        # 2. Recognized command + detected language
        cmd = ttk.LabelFrame(body, text="Recognized command", padding=8)
        cmd.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        cmd.columnconfigure(0, weight=1)
        self.command_label = tk.Label(cmd, text="-", bg=LIGHT, fg=NAVY, anchor="w",
                                      font=("Arial", 20, "bold"))
        self.command_label.grid(row=0, column=0, sticky="ew")
        self.language_label = tk.Label(cmd, text="", bg=LIGHT, fg=BLUE, font=("Arial", 10))
        self.language_label.grid(row=0, column=1, padx=8)

        # 3 + 4. Understanding and execution status side by side
        mid = ttk.Frame(body)
        mid.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        mid.columnconfigure(0, weight=1)
        mid.columnconfigure(1, weight=1)

        und = ttk.LabelFrame(mid, text="Understanding", padding=8)
        und.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.understanding_label = tk.Label(und, text="-", bg=LIGHT, anchor="w",
                                            font=("Arial", 12))
        self.understanding_label.pack(fill="x")

        exe = ttk.LabelFrame(mid, text="Execution status", padding=8)
        exe.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.status_badge = tk.Label(exe, text="", width=24, fg=WHITE, pady=4,
                                     font=("Arial", 11, "bold"))
        self.status_badge.pack(anchor="w")

        # 5. Result (read-only)
        res = ttk.LabelFrame(body, text="Result", padding=8)
        res.grid(row=3, column=0, sticky="nsew", pady=(0, 8))
        res.columnconfigure(0, weight=1)
        res.rowconfigure(0, weight=1)
        self.result_text = ScrolledText(res, height=6, wrap="word", font=("Arial", 12),
                                        state="disabled", bg=WHITE)
        self.result_text.grid(row=0, column=0, sticky="nsew")

        # 6. History (newest first)
        hist = ttk.LabelFrame(body, text="Command history", padding=8)
        hist.grid(row=4, column=0, sticky="nsew")
        hist.columnconfigure(0, weight=1)
        hist.rowconfigure(0, weight=1)
        cols = ("time", "command", "intent", "status")
        self.history = ttk.Treeview(hist, columns=cols, show="headings", height=6)
        for col, title, width in (("time", "Time", 90), ("command", "Command", 360),
                                  ("intent", "Intent", 170), ("status", "Status", 140)):
            self.history.heading(col, text=title)
            self.history.column(col, width=width, anchor="w")
        scroll = ttk.Scrollbar(hist, orient="vertical", command=self.history.yview)
        self.history.configure(yscrollcommand=scroll.set)
        self.history.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

    def _build_status_bar(self, workspace: str) -> None:
        bar = tk.Frame(self.root, bg=NAVY)
        bar.pack(fill="x", side="bottom")
        self.info_label = tk.Label(bar, bg=NAVY, fg=WHITE, anchor="w", font=("Arial", 9))
        self.info_label.pack(fill="x", padx=12, pady=3)
        self._info = {"folder": workspace, "mic": "default", "model": "stand-in"}
        self._refresh_info()

    def set_info(self, **kwargs: str) -> None:
        """Update status-bar fields: folder=..., mic=..., model=... (GUI thread only)."""
        self._info.update({k: v for k, v in kwargs.items() if k in self._info})
        self._refresh_info()

    def _refresh_info(self) -> None:
        voice = "available" if speaker.is_available() else "espeak-ng missing"
        self.info_label.config(
            text=f"Folder: {self._info['folder']}   |   Microphone: {self._info['mic']}"
                 f"   |   Speech model: {self._info['model']}   |   Voice: {voice}")

    # ------------------------------------------------------- display helpers
    def set_state(self, state: str) -> None:
        self.state_label.config(text=state.capitalize(),
                                bg=STATE_COLORS.get(state, STATE_COLORS["ready"]))

    def set_execution(self, status: Optional[str]) -> None:
        if status is None:
            self.status_badge.config(text="-", bg="#9E9E9E")
            return
        self.status_badge.config(text=EXECUTION_STATUSES.get(status, status),
                                 bg=STATUS_COLORS.get(status, "#9E9E9E"))

    def set_result(self, text: str) -> None:
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", shape(text))
        self.result_text.config(state="disabled")

    def _reset_for_new_command(self) -> None:
        self._current = {"command": "", "intent": ""}
        self.command_label.config(text="Listening...")
        self.language_label.config(text="")
        self.understanding_label.config(text="-", fg="black")
        self.set_execution(None)
        self.set_result("")

    def _add_history(self, status: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self.history.insert("", 0, values=(                     # index 0 = newest first
            stamp,
            shape(self._current["command"]) or "-",
            self._current["intent"] or "-",
            EXECUTION_STATUSES.get(status, status),
        ))

    # ------------------------------------------------------------ event entry
    def on_event(self, event: Event) -> None:
        """Interface from Section 9. GUI thread only; threads use emit() instead."""
        stage, state, text = event.stage, event.state, event.text

        if stage == "listening":
            self.set_state(state)
        elif stage == "command":
            self._current["command"] = text
            self.command_label.config(text=shape(text) or "-")
            self.language_label.config(
                text={"en": "English", "ar": "Arabic"}.get(state, state))
        elif stage == "understanding":
            self._current["intent"] = text
            color = {"allowed": "#2E7D32", "rejected": "#C62828"}.get(state, "#EF6C00")
            self.understanding_label.config(
                text=f"{text}  |  {UNDERSTANDING_LABELS.get(state, state)}", fg=color)
        elif stage == "execution":
            self.set_execution(state)
            if state in TERMINAL_EXECUTION:
                self._add_history(state)
        elif stage == "result":
            self.set_result(text)      # speech was already queued by emit()
        elif stage == "error":
            self.set_state("error")
            self.set_execution("failed")
            self.set_result(text)
            self._add_history("failed")

    def emit(self, event: Event) -> None:
        """Thread-safe: hand this to any worker thread."""
        if event.stage == "result":
            # Queue the spoken reply here (worker thread) so the pipeline's
            # tts-join sees it and Listen stays disabled until speech is done.
            self._enqueue_speech(event.text, event.state)
        self._queue.put(event)

    # ----------------------------------------------------------- Listen / run
    def start_listening(self) -> None:
        if self._busy or self._closing:
            return
        self._busy = True
        self.listen_btn.state(["disabled"])
        self._reset_for_new_command()
        language = self.lang_var.get()
        threading.Thread(target=self._run_pipeline, args=(language,), daemon=True).start()

    def _run_pipeline(self, language: str) -> None:
        """Worker thread. No Tkinter calls here, only queue.put()."""
        try:
            self.pipeline(self.emit, language, self.confirm)
        except Exception as exc:  # a module failing must never crash the GUI
            self.emit(Event("error", "failed", f"Something went wrong: {exc}"))
        finally:
            self._tts_queue.join()           # let the spoken reply finish first
            self.emit(Event("listening", "ready"))
            self._queue.put(_DONE)

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self._queue.get_nowait()
                if item is _DONE:
                    self._busy = False
                    self.listen_btn.state(["!disabled"])
                elif isinstance(item, _ConfirmRequest):
                    self._show_confirmation(item)
                elif isinstance(item, Event):
                    self.on_event(item)
        except queue.Empty:
            pass
        if not self._closing:
            self.root.after(POLL_MS, self._poll_queue)

    # --------------------------------------------------------- text-to-speech
    def _on_voice_toggle(self) -> None:
        self._voice_on = bool(self.voice_var.get())
        if not self._voice_on:
            speaker.stop()

    def _enqueue_speech(self, message: str, language: str) -> None:
        if self._voice_on and message:
            self._tts_queue.put((message, language))

    def _tts_loop(self) -> None:
        """Daemon thread: speaks queued replies one at a time."""
        while True:
            item = self._tts_queue.get()
            try:
                if item is _STOP_TTS:
                    return
                message, language = item
                if self._closing or not self._voice_on:
                    continue
                self.emit(Event("listening", "speaking"))
                self._speak(message, language)
                self.emit(Event("listening", "processing" if self._busy else "ready"))
            finally:
                self._tts_queue.task_done()

    # ------------------------------------------------------------ confirmation
    def confirm(self, prompt: str) -> bool:
        """Called from the pipeline thread. Blocks until the user answers (or 10 s)."""
        request = _ConfirmRequest(prompt, self.lang_var.get())
        self._queue.put(request)
        request.done.wait(CONFIRM_TIMEOUT_SECONDS + 3)
        return request.answer

    def _show_confirmation(self, request: _ConfirmRequest) -> None:
        win = tk.Toplevel(self.root)
        self._confirm_win = win
        win.title("Confirm")
        win.configure(bg=LIGHT, padx=20, pady=16)
        win.transient(self.root)
        win.resizable(False, False)

        tk.Label(win, text=shape(request.prompt), bg=LIGHT, fg=NAVY, wraplength=380,
                 font=("Arial", 13, "bold")).pack(pady=(0, 8))
        countdown = tk.Label(win, bg=LIGHT, fg="#C62828", font=("Arial", 10))
        countdown.pack(pady=(0, 10))

        remaining = [CONFIRM_TIMEOUT_SECONDS]

        def answer(value: bool) -> None:
            if request.done.is_set():
                return
            request.answer = value
            request.done.set()
            self._confirm_win = None
            win.destroy()

        def tick() -> None:
            if request.done.is_set():
                return
            if remaining[0] <= 0:
                answer(False)                      # auto-cancel after 10 s
                return
            countdown.config(text=f"Auto-cancel in {remaining[0]} s")
            remaining[0] -= 1
            win.after(1000, tick)

        buttons = tk.Frame(win, bg=LIGHT)
        buttons.pack()
        yes_text, no_text = ("نعم", "لا") if request.language == "ar" else ("Yes", "No")
        ttk.Button(buttons, text=shape(yes_text), command=lambda: answer(True)).pack(side="left", padx=6)
        ttk.Button(buttons, text=shape(no_text), command=lambda: answer(False)).pack(side="left", padx=6)
        win.protocol("WM_DELETE_WINDOW", lambda: answer(False))   # closing = No

        self._enqueue_speech(request.prompt, request.language)
        win.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - win.winfo_height()) // 3
        win.geometry(f"+{x}+{y}")
        win.grab_set()
        tick()

    # ------------------------------------------------------------------ close
    def close(self) -> None:
        self._closing = True
        speaker.stop()
        self._tts_queue.put(_STOP_TTS)
        if self._confirm_win is not None:
            self._confirm_win.destroy()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
