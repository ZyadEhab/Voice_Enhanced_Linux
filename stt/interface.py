"""
stt/interface.py  --  Contract between Speech-to-Text and the rest of the pipeline.
Owner: Speech-to-Text Engineer.  Neighbours to confirm: NLP, GUI, Team Leader (main.py).

Pipeline slice:   Microphone -> record() -> transcribe(audio) -> understand(text, language)

OS concepts shown: I/O (microphone device as input stream), threads (blocking
transcribe runs in a worker thread so the GUI stays responsive), error handling.
"""
from dataclasses import dataclass
from typing import Optional

SUPPORTED_LANGUAGES = ("en", "ar")

# ---- Audio format produced by stt/recorder.py and accepted by transcribe() ----
SAMPLE_RATE = 16_000          # Hz
CHANNELS = 1                  # mono
DTYPE = "float32"             # numpy array, shape (n_samples,), values in [-1.0, 1.0]


# ---- Errors: raised to the main loop, which shows "Error" in the GUI then "Ready" ----
class MicrophoneError(Exception):
    """No input device, device busy, or permission denied."""


class TranscriptionError(Exception):
    """Model failed to load or recognition crashed."""


# ---- The agreed contract (matches Section 9 of PROJECT_CONTEXT.md) ----
def transcribe(audio, language: Optional[str] = None) -> tuple[str, str]:
    """
    audio    : numpy float32 array, 16 kHz, mono (see constants above).
    language : optional hint "en" / "ar" (e.g. from the GUI language switch). None = auto-detect.
               Added in Task 3; callers that pass only `audio` keep working.

    Returns (text, language):
      text     : str, never None. Stripped, single spaces. Raw Whisper output:
                 NO lowercasing, NO diacritic removal, NO letter unification
                 (the NLP module owns normalization).
                 "" (empty string) when: silence, too short, or language not in
                 SUPPORTED_LANGUAGES.
      language : "en" or "ar" when text is not empty, otherwise "".

    Raises MicrophoneError / TranscriptionError (never returns an error string).
    Blocking call: run it in a worker thread, not in the Tkinter thread.
    The Whisper model is loaded once on first use (first call is slower).
    """
    from .transcriber import transcribe as _impl   # lazy: keeps this file light to import
    return _impl(audio, language)


# ---- Optional richer result for the GUI status bar / logs / tests ----
@dataclass
class TranscriptionResult:
    text: str
    language: str                              # "en" | "ar" | ""
    detected_language: Optional[str] = None    # raw Whisper code, even if unsupported
    language_probability: Optional[float] = None
    duration_s: float = 0.0                    # length of the recorded audio
    reason: Optional[str] = None               # "silence" | "too_short" | "unsupported_language" | None


def transcribe_detailed(audio, language: Optional[str] = None) -> TranscriptionResult:
    """Same work as transcribe(), but keeps the extra info. transcribe() is a thin wrapper."""
    from .transcriber import transcribe_detailed as _impl
    return _impl(audio, language)


# ---- Events sent to the GUI queue:  Event(stage="stt", state=..., text=...) ----
STT_STATES = {
    "listening":  "microphone open, waiting for speech",
    "processing": "recording finished, transcribing",
    "completed":  "text recognized (text field holds it)",
    "no_speech":  "empty text; ask the user to repeat",
    "error":      "MicrophoneError / TranscriptionError",
}

# ---- Rule for the main loop (main.py) ----
# text, language = transcribe(audio)
# if not text:  emit(stage="stt", state="no_speech");  return   # understand() is NOT called
# intent = understand(text, language)
