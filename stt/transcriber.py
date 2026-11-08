"""
stt/transcriber.py  --  Offline speech-to-text with faster-whisper (Task 2 + Task 3).

Spec (PROJECT_CONTEXT 10.1): WhisperModel("small", device="cpu", compute_type="int8"),
beam_size=5, vad_filter=True, model loaded once on first use, language auto-detected,
language not in ("en", "ar") -> empty text.

Task 3 accuracy options (each can be switched off in Settings so stt/evaluate.py can measure it):
  use_prompt        : hint the allow-listed command words to Whisper (stt/vocabulary.py)
  preprocess        : remove DC offset, trim silence, raise gain (stt/audio_utils.py)
  language_fallback : when language detection is unsure, also try English and Arabic
                      and keep the most confident result
Still raw output: no lowercasing or letter unification here. The NLP module owns that.
"""
import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np

from . import audio_utils, vocabulary
from .interface import (SAMPLE_RATE, SUPPORTED_LANGUAGES, TranscriptionError,
                        TranscriptionResult)
from .metrics import is_prompt_echo
from .recorder import has_speech

MODEL_SIZE = "small"
MIN_DURATION_S = 0.3          # shorter recordings are treated as "too short"
MIN_LANGUAGE_PROB = 0.6       # below this, auto language detection is "unsure" (tune with evaluate.py)
MIN_AVG_LOGPROB = -1.0        # forced-language results below this confidence are rejected (tune)

_model = None
_model_lock = threading.Lock()


@dataclass
class Settings:
    use_prompt: bool = True
    preprocess: bool = True
    language_fallback: bool = True


SETTINGS = Settings()


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


def _run(model, audio: np.ndarray, language: Optional[str], use_prompt: bool):
    """One Whisper pass. Returns (text, mean avg_logprob or None, info)."""
    prompt = vocabulary.prompt_for(language) if use_prompt else None
    segments, info = model.transcribe(
        audio, beam_size=5, vad_filter=True, language=language,
        initial_prompt=prompt, condition_on_previous_text=False, temperature=0.0)
    segs = list(segments)
    text = " ".join(" ".join(seg.text for seg in segs).split())
    logprobs = [seg.avg_logprob for seg in segs if hasattr(seg, "avg_logprob")]
    avg = sum(logprobs) / len(logprobs) if logprobs else None
    if prompt and is_prompt_echo(text, prompt):      # Whisper repeated our hint on noise
        text = ""
    return text, avg, info


def transcribe_detailed(audio, language: Optional[str] = None,
                        settings: Optional[Settings] = None) -> TranscriptionResult:
    """language: optional hint "en" or "ar" (e.g. from the GUI language switch); None = auto-detect."""
    cfg = settings or SETTINGS
    if language not in SUPPORTED_LANGUAGES:
        language = None
    audio = _prepare(audio)
    duration = len(audio) / SAMPLE_RATE

    if duration < MIN_DURATION_S:
        return TranscriptionResult("", "", duration_s=duration, reason="too_short")
    if not has_speech(audio):
        return TranscriptionResult("", "", duration_s=duration, reason="silence")

    work = audio_utils.preprocess(audio) if cfg.preprocess else audio
    model = _get_model()
    try:
        text, avg, info = _run(model, work, language, cfg.use_prompt)
        detected: Optional[str] = getattr(info, "language", None)
        probability: Optional[float] = getattr(info, "language_probability", None)
        chosen = detected

        unsure = (language is None and cfg.language_fallback and
                  (detected not in SUPPORTED_LANGUAGES or
                   (probability is not None and probability < MIN_LANGUAGE_PROB)))
        if unsure:
            candidates = []
            if text and detected in SUPPORTED_LANGUAGES:
                candidates.append((avg if avg is not None else 0.0, text, detected))
            for lang in SUPPORTED_LANGUAGES:
                t, a, _ = _run(model, work, lang, cfg.use_prompt)
                a = a if a is not None else 0.0
                if t and a >= MIN_AVG_LOGPROB:
                    candidates.append((a, t, lang))
            if candidates:
                _, text, chosen = max(candidates)
            else:
                text = ""
    except TranscriptionError:
        raise
    except Exception as exc:
        raise TranscriptionError(f"Recognition failed: {exc}") from exc

    if not text:
        reason = ("unsupported_language"
                  if detected is not None and detected not in SUPPORTED_LANGUAGES else "silence")
        return TranscriptionResult("", "", detected, probability, duration, reason)
    if chosen not in SUPPORTED_LANGUAGES:
        return TranscriptionResult("", "", detected, probability, duration, "unsupported_language")
    return TranscriptionResult(text, chosen, detected, probability, duration, None)


def transcribe(audio, language: Optional[str] = None) -> tuple:
    """Contract function: audio -> (text, language). See stt/interface.py."""
    result = transcribe_detailed(audio, language)
    return result.text, result.language
