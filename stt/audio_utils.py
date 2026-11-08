"""
stt/audio_utils.py  --  Small, safe clean-ups applied to the recording before Whisper.

Order matters: remove DC offset -> trim silence -> raise gain. (Trimming runs before
the gain step so amplified background noise cannot be mistaken for speech.)
"""
import numpy as np

from .interface import SAMPLE_RATE
from .recorder import BLOCK_SIZE, SILENCE_RMS, block_rms


def remove_dc(audio: np.ndarray) -> np.ndarray:
    """Remove the constant offset some microphones add."""
    if audio.size == 0:
        return audio
    return (audio - float(np.mean(audio))).astype(np.float32)


def trim_silence(audio: np.ndarray, threshold: float = SILENCE_RMS * 0.5,
                 pad_s: float = 0.25) -> np.ndarray:
    """Cut leading/trailing silence but keep `pad_s` around the speech."""
    loud = [i for i in range(0, len(audio), BLOCK_SIZE)
            if block_rms(audio[i:i + BLOCK_SIZE]) >= threshold]
    if not loud:
        return audio
    pad = int(pad_s * SAMPLE_RATE)
    start = max(0, loud[0] - pad)
    end = min(len(audio), loud[-1] + BLOCK_SIZE + pad)
    return audio[start:end]


def normalize_gain(audio: np.ndarray, target_peak: float = 0.9, max_gain: float = 20.0,
                   min_peak: float = 0.01, loud_enough: float = 0.5) -> np.ndarray:
    """Amplify quiet recordings (common in virtual machines). Leaves loud or empty audio alone."""
    if audio.size == 0:
        return audio
    peak = float(np.percentile(np.abs(audio), 99.5))
    if peak < min_peak or peak >= loud_enough:
        return audio
    gain = min(target_peak / peak, max_gain)
    return np.clip(audio * gain, -1.0, 1.0).astype(np.float32)


def preprocess(audio: np.ndarray) -> np.ndarray:
    return normalize_gain(trim_silence(remove_dc(audio)))
