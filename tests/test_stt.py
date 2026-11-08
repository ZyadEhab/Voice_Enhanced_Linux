"""Tests for the STT module that need no microphone and no Whisper download."""
from types import SimpleNamespace

import numpy as np
import pytest

from stt import interface, recorder, transcriber
from stt.interface import SAMPLE_RATE, TranscriptionError

BLOCK = recorder.BLOCK_SIZE


def loud(n_blocks):
    return [np.full(BLOCK, 0.1, dtype=np.float32) for _ in range(n_blocks)]


def quiet(n_blocks):
    return [np.zeros(BLOCK, dtype=np.float32) for _ in range(n_blocks)]


def run_endpointer(blocks, **kw):
    ep = recorder.SilenceEndpointer(**kw)
    for i, b in enumerate(blocks, 1):
        if ep.feed(b):
            return i
    return None


# ---------- endpointing ----------
def test_stops_after_one_second_of_silence_following_speech():
    stopped_at = run_endpointer(loud(5) + quiet(20))
    assert stopped_at == 5 + 10          # 10 silent blocks = 1.0 s


def test_does_not_stop_on_silence_before_speech():
    assert run_endpointer(quiet(50)) is None   # 5 s of silence, still waiting


def test_max_duration_is_enforced():
    assert run_endpointer(loud(200)) == 100    # 10 s cap


def test_single_click_is_not_speech():
    ep = recorder.SilenceEndpointer()
    for b in loud(1) + quiet(30):
        ep.feed(b)
    assert not ep.speech_started


# ---------- transcriber contract ----------
class FakeModel:
    def __init__(self, text, language, prob=0.9):
        self.text, self.language, self.prob = text, language, prob

    def transcribe(self, audio, beam_size, vad_filter):
        segs = [SimpleNamespace(text=t) for t in self.text.split("|")] if self.text else []
        return iter(segs), SimpleNamespace(language=self.language, language_probability=self.prob)


@pytest.fixture
def speech_audio():
    return np.concatenate(loud(20)).astype(np.float32)    # 2 s of "speech"


def use_model(monkeypatch, model):
    monkeypatch.setattr(transcriber, "_model", model)


def test_english_result(monkeypatch, speech_audio):
    use_model(monkeypatch, FakeModel("  Open   Firefox ", "en"))
    assert interface.transcribe(speech_audio) == ("Open Firefox", "en")


def test_arabic_text_is_kept_raw(monkeypatch, speech_audio):
    use_model(monkeypatch, FakeModel("افتح| فايرفوكس.", "ar"))
    text, lang = interface.transcribe(speech_audio)
    assert text == "افتح فايرفوكس." and lang == "ar"      # punctuation kept: NLP normalizes


def test_unsupported_language_gives_empty(monkeypatch, speech_audio):
    use_model(monkeypatch, FakeModel("bonjour", "fr"))
    result = interface.transcribe_detailed(speech_audio)
    assert (result.text, result.language) == ("", "")
    assert result.reason == "unsupported_language" and result.detected_language == "fr"


def test_silence_skips_the_model(monkeypatch):
    use_model(monkeypatch, None)       # would crash if the model were touched
    audio = np.zeros(SAMPLE_RATE * 2, dtype=np.float32)
    assert interface.transcribe(audio) == ("", "")
    assert interface.transcribe_detailed(audio).reason == "silence"


def test_too_short(monkeypatch):
    use_model(monkeypatch, None)
    audio = np.full(int(SAMPLE_RATE * 0.1), 0.1, dtype=np.float32)
    assert interface.transcribe_detailed(audio).reason == "too_short"
    assert interface.transcribe(None) == ("", "")


def test_empty_model_output_is_silence(monkeypatch, speech_audio):
    use_model(monkeypatch, FakeModel("", "en"))
    assert interface.transcribe_detailed(speech_audio).reason == "silence"


def test_model_crash_becomes_transcription_error(monkeypatch, speech_audio):
    class Broken:
        def transcribe(self, *a, **k):
            raise RuntimeError("boom")
    use_model(monkeypatch, Broken())
    with pytest.raises(TranscriptionError):
        interface.transcribe(speech_audio)
