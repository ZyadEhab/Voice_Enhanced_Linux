"""
stt/recorder.py  --  Microphone capture for one voice command.

Spec (PROJECT_CONTEXT 10.1): sounddevice InputStream, 16 kHz, mono, float32,
0.1 s blocks, stop after ~1 s of silence once speech has started, max 10 s,
silence threshold RMS ~0.01 (tune per microphone), default input device.

OS concept: the microphone is an input device read through a callback; the audio
driver thread fills a queue and this function consumes it (producer/consumer).
"""
import queue
import threading
from typing import Callable, Optional

import numpy as np

from .interface import CHANNELS, DTYPE, SAMPLE_RATE, MicrophoneError

BLOCK_S = 0.1                              # seconds per audio block
BLOCK_SIZE = int(SAMPLE_RATE * BLOCK_S)    # samples per block
SILENCE_RMS = 0.01                         # below this a block counts as silence (tune per mic)
SILENCE_END_S = 1.0                        # stop after this much silence once speech started
MAX_S = 10.0                               # hard limit for one command
MIN_SPEECH_BLOCKS = 2                      # loud blocks needed before "speech started" (~0.2 s)


def block_rms(block: np.ndarray) -> float:
    """Root-mean-square loudness of one block (0.0 for an empty block)."""
    if block.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(block, dtype=np.float64))))


class SilenceEndpointer:
    """Decides when the user has finished speaking. Pure logic: easy to unit test."""

    def __init__(self, threshold: float = SILENCE_RMS, silence_end_s: float = SILENCE_END_S,
                 max_s: float = MAX_S, block_s: float = BLOCK_S):
        self.threshold = threshold
        self._silence_limit = round(silence_end_s / block_s)
        self._max_blocks = round(max_s / block_s)
        self.speech_started = False
        self._loud = 0
        self._silent_run = 0
        self.total_blocks = 0

    def feed(self, block: np.ndarray) -> bool:
        """Give one block; returns True when recording should stop."""
        self.total_blocks += 1
        if block_rms(block) >= self.threshold:
            self._loud += 1
            self._silent_run = 0
            if self._loud >= MIN_SPEECH_BLOCKS:
                self.speech_started = True
        else:
            self._silent_run += 1
        if self.speech_started and self._silent_run >= self._silence_limit:
            return True
        return self.total_blocks >= self._max_blocks


def has_speech(audio: np.ndarray, threshold: float = SILENCE_RMS * 0.5) -> bool:
    """True if at least MIN_SPEECH_BLOCKS blocks are louder than the (lenient) threshold.
    Used by the transcriber to skip pure silence, which Whisper can hallucinate on."""
    loud = 0
    for start in range(0, len(audio), BLOCK_SIZE):
        if block_rms(audio[start:start + BLOCK_SIZE]) >= threshold:
            loud += 1
            if loud >= MIN_SPEECH_BLOCKS:
                return True
    return False


def record(max_seconds: float = MAX_S,
           stop_event: Optional[threading.Event] = None,
           on_speech_start: Optional[Callable[[], None]] = None) -> np.ndarray:
    """
    Record one command from the default microphone.

    Returns a float32 numpy array, shape (n_samples,), 16 kHz mono
    (empty array if stopped before any audio arrived).
    stop_event      : set it from another thread to stop early (e.g. GUI Stop button).
    on_speech_start : called once when speech is detected (GUI can show "Listening...").
    Raises MicrophoneError if there is no usable microphone.
    """
    try:
        import sounddevice as sd
    except (ImportError, OSError) as exc:   # OSError: PortAudio library missing
        raise MicrophoneError(
            "Audio library not available. Install: sudo apt install portaudio19-dev "
            "and pip install sounddevice") from exc

    try:
        sd.query_devices(kind="input")
    except (ValueError, sd.PortAudioError) as exc:
        raise MicrophoneError("No microphone found") from exc

    audio_queue: "queue.Queue[np.ndarray]" = queue.Queue()

    def callback(indata, frames, time_info, status):   # runs in the audio driver thread
        audio_queue.put(indata[:, 0].copy())

    endpointer = SilenceEndpointer(max_s=max_seconds)
    blocks = []
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE,
                            blocksize=BLOCK_SIZE, callback=callback):
            while True:
                if stop_event is not None and stop_event.is_set():
                    break
                try:
                    block = audio_queue.get(timeout=1.0)
                except queue.Empty:
                    raise MicrophoneError("The microphone is not delivering audio")
                blocks.append(block)
                was_started = endpointer.speech_started
                done = endpointer.feed(block)
                if on_speech_start and not was_started and endpointer.speech_started:
                    on_speech_start()
                if done:
                    break
    except sd.PortAudioError as exc:
        raise MicrophoneError(f"Microphone error: {exc}") from exc

    if not blocks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(blocks).astype(np.float32)
