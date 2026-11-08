"""Speech-to-text package. Public API: record(), transcribe(), transcribe_detailed()."""
from .interface import (MicrophoneError, TranscriptionError, TranscriptionResult,
                        transcribe, transcribe_detailed)
from .recorder import record

__all__ = ["record", "transcribe", "transcribe_detailed", "TranscriptionResult",
           "MicrophoneError", "TranscriptionError"]
