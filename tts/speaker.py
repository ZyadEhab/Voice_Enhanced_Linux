"""Spoken replies with espeak-ng (English + Arabic).

Interface (PROJECT_CONTEXT.md, Section 9):  speak(message, language) -> spoken audio

OS concepts demonstrated
------------------------
* Process management : espeak-ng runs as a child process started with Popen.
                       stop() terminates it, e.g. when the window is closed.
* Shell / security   : the command is an argument LIST (never shell=True) and the
                       message travels through stdin, so spoken or typed text can
                       never be interpreted as a shell command or as an option.
* I/O redirection    : stdin is a pipe; stdout/stderr go to /dev/null (DEVNULL) so
                       ALSA / audio warnings never pollute the terminal or GUI.

speak() is BLOCKING (returns when the speech has finished). Call it from a
background thread, never from the Tkinter main thread. The GUI does exactly that.
speak() never raises: it returns True/False so a TTS problem cannot crash the app.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import threading

ESPEAK = "espeak-ng"

# language code -> espeak-ng voice. Anything else falls back to English.
VOICES = {"en": "en-us", "ar": "ar"}
SPEED_WPM = 150
MAX_CHARS = 500          # replies are short; this also bounds the process lifetime
TIMEOUT_SECONDS = 30

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_WHITESPACE = re.compile(r"\s+")

_lock = threading.Lock()
_current: subprocess.Popen | None = None


def is_available() -> bool:
    """True if espeak-ng is installed (sudo apt install espeak-ng)."""
    return shutil.which(ESPEAK) is not None


def _clean(message: str | None) -> str:
    """Make the message safe and speakable: no control chars, one line, bounded."""
    if not message:
        return ""
    text = _CONTROL_CHARS.sub(" ", str(message))
    text = _WHITESPACE.sub(" ", text).strip()
    return text[:MAX_CHARS]


def build_command(language: str) -> list[str]:
    """The exact argument list that is executed (exposed so tests can inspect it)."""
    voice = VOICES.get(language, VOICES["en"])
    return [ESPEAK, "-v", voice, "-s", str(SPEED_WPM), "--stdin"]


def speak(message: str, language: str = "en") -> bool:
    """Speak `message` aloud. Returns True if it was spoken, False otherwise."""
    global _current
    text = _clean(message)
    if not text or not is_available():
        return False

    try:
        with _lock:
            proc = subprocess.Popen(
                build_command(language),
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            _current = proc
        try:
            proc.communicate(text.encode("utf-8"), timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return False
        return proc.returncode == 0
    except OSError:
        return False
    finally:
        with _lock:
            if _current is not None and _current.poll() is not None:
                _current = None


def stop() -> None:
    """Interrupt speech that is in progress (safe to call when idle)."""
    global _current
    with _lock:
        proc, _current = _current, None
    if proc is not None and proc.poll() is None:
        try:
            proc.terminate()
        except OSError:
            pass
