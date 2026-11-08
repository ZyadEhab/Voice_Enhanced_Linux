"""
stt/transcriber.py  --  Offline speech-to-text with faster-whisper.

Spec (PROJECT_CONTEXT 10.1): WhisperModel("small", device="cpu", compute_type="int8"),
beam_size=5, vad_filter=True, model loaded once on first use, language auto-detected,
language not in ("en", "ar") -> empty text.
"""
import threading
from typing import Optional

import numpy as np

from .interface import (SAMPLE_RATE, SUPPORTED_LANGUAGES, TranscriptionError,
                        TranscriptionResult)
from .recorder import has_speech

MODEL_SIZE = "small"
MIN_DURATION_S = 0.3          # shorter recordings are treated as "too short"

_model = None
_model_lock = threading.Lock()


def _get_model():
    """Load the Whisper model once (first call downloads it, then works offline)."""
    global _model
    with _model_lock:
        if _model is None:
            try:
                from faster_whisper import WhisperModel
                _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
            except Exception as exc:
                raise TranscriptionError(f"Could not load the speech model: {exc}") from exc
        return _model


def _prepare(audio) -> np.ndarray:
    if audio is None:
        return np.zeros(0, dtype=np.float32)
    return np.asarray(audio, dtype=np.float32).reshape(-1)


def transcribe_detailed(audio) -> TranscriptionResult:
    audio = _prepare(audio)
    duration = len(audio) / SAMPLE_RATE

    if duration < MIN_DURATION_S:
        return TranscriptionResult("", "", duration_s=duration, reason="too_short")
    if not has_speech(audio):
        return TranscriptionResult("", "", duration_s=duration, reason="silence")

    model = _get_model()
    try:
        segments, info = model.transcribe(audio, beam_size=5, vad_filter=True)
        text = " ".join(" ".join(seg.text for seg in segments).split())
    except Exception as exc:
        raise TranscriptionError(f"Recognition failed: {exc}") from exc

    detected: Optional[str] = getattr(info, "language", None)
    probability: Optional[float] = getattr(info, "language_probability", None)

    if not text:
        return TranscriptionResult("", "", detected, probability, duration, "silence")
    if detected not in SUPPORTED_LANGUAGES:
        return TranscriptionResult("", "", detected, probability, duration, "unsupported_language")
    return TranscriptionResult(text, detected, detected, probability, duration, None)


def transcribe(audio) -> tuple:
    """Contract function: audio -> (text, language). See stt/interface.py."""
    result = transcribe_detailed(audio)
    return result.text, result.language
