"""Tests for the STT module that need no microphone and no Whisper download."""
from types import SimpleNamespace

import numpy as np
import pytest

from stt import audio_utils, interface, metrics, recorder, transcriber, vocabulary
from stt.interface import SAMPLE_RATE, TranscriptionError
from stt.transcriber import Settings

BLOCK = recorder.BLOCK_SIZE
AR_OPEN_FIREFOX = "\u0627\u0641\u062a\u062d \u0641\u0627\u064a\u0631\u0641\u0648\u0643\u0633"


def loud(n_blocks, level=0.1):
    return [np.full(BLOCK, level, dtype=np.float32) for _ in range(n_blocks)]


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
    assert run_endpointer(loud(5) + quiet(20)) == 5 + 10


def test_does_not_stop_on_silence_before_speech():
    assert run_endpointer(quiet(50)) is None


def test_max_duration_is_enforced():
    assert run_endpointer(loud(200)) == 100


def test_single_click_is_not_speech():
    ep = recorder.SilenceEndpointer()
    for b in loud(1) + quiet(30):
        ep.feed(b)
    assert not ep.speech_started


# ---------- fake Whisper ----------
class FakeModel:
    """true_language: language the audio really is. detected: what auto-detection claims.
    Forced runs in the right language get a good logprob, forced runs in a wrong one a bad logprob."""
    def __init__(self, text, true_language, detected=None, prob=0.9):
        self.text, self.true = text, true_language
        self.detected = detected or true_language
        self.prob = prob
        self.calls = []

    def transcribe(self, audio, **kw):
        language = kw.get("language")
        self.calls.append(kw)
        shown = language or self.detected
        logprob = -0.2 if shown == self.true else -2.0
        segs = [SimpleNamespace(text=t, avg_logprob=logprob) for t in self.text.split("|")] if self.text else []
        prob = 1.0 if language else self.prob
        return iter(segs), SimpleNamespace(language=shown, language_probability=prob)


@pytest.fixture
def speech_audio():
    return np.concatenate(loud(20)).astype(np.float32)    # 2 s of "speech"


def use_model(monkeypatch, model):
    monkeypatch.setattr(transcriber, "_model", model)


# ---------- transcriber contract (kept from Task 2) ----------
def test_english_result(monkeypatch, speech_audio):
    use_model(monkeypatch, FakeModel("  Open   Firefox ", "en"))
    assert interface.transcribe(speech_audio) == ("Open Firefox", "en")


def test_arabic_text_is_kept_raw(monkeypatch, speech_audio):
    use_model(monkeypatch, FakeModel("\u0627\u0641\u062a\u062d| \u0641\u0627\u064a\u0631\u0641\u0648\u0643\u0633.", "ar"))
    text, lang = interface.transcribe(speech_audio)
    assert text == AR_OPEN_FIREFOX + "." and lang == "ar"      # punctuation kept: NLP normalizes


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


# ---------- Task 3: accuracy options ----------
def test_prompt_and_stable_decoding_are_sent_to_whisper(monkeypatch, speech_audio):
    model = FakeModel("Open Firefox", "en")
    use_model(monkeypatch, model)
    interface.transcribe(speech_audio)
    call = model.calls[0]
    assert call["initial_prompt"] == vocabulary.prompt_for(None)
    assert call["condition_on_previous_text"] is False and call["temperature"] == 0.0


def test_baseline_settings_send_no_prompt(monkeypatch, speech_audio):
    model = FakeModel("Open Firefox", "en")
    use_model(monkeypatch, model)
    off = Settings(use_prompt=False, preprocess=False, language_fallback=False)
    transcriber.transcribe_detailed(speech_audio, settings=off)
    assert model.calls[0]["initial_prompt"] is None and len(model.calls) == 1


def test_language_hint_forces_one_pass(monkeypatch, speech_audio):
    model = FakeModel(AR_OPEN_FIREFOX, "ar", detected="fr", prob=0.3)
    use_model(monkeypatch, model)
    text, lang = interface.transcribe(speech_audio, language="ar")
    assert (text, lang) == (AR_OPEN_FIREFOX, "ar")
    assert len(model.calls) == 1 and model.calls[0]["language"] == "ar"
    assert model.calls[0]["initial_prompt"] == vocabulary.PROMPT_AR


def test_bad_language_hint_is_ignored(monkeypatch, speech_audio):
    model = FakeModel("Open Firefox", "en")
    use_model(monkeypatch, model)
    assert interface.transcribe(speech_audio, language="xx") == ("Open Firefox", "en")
    assert model.calls[0]["language"] is None


def test_misdetected_language_is_rescued_by_fallback(monkeypatch, speech_audio):
    use_model(monkeypatch, FakeModel(AR_OPEN_FIREFOX, "ar", detected="fr", prob=0.4))
    result = interface.transcribe_detailed(speech_audio)
    assert (result.text, result.language) == (AR_OPEN_FIREFOX, "ar")
    assert result.detected_language == "fr"


def test_fallback_can_be_disabled(monkeypatch, speech_audio):
    use_model(monkeypatch, FakeModel(AR_OPEN_FIREFOX, "ar", detected="fr", prob=0.4))
    off = Settings(use_prompt=True, preprocess=True, language_fallback=False)
    result = transcriber.transcribe_detailed(speech_audio, settings=off)
    assert result.text == "" and result.reason == "unsupported_language"


def test_unsure_but_supported_language_keeps_best_candidate(monkeypatch, speech_audio):
    use_model(monkeypatch, FakeModel("Open Firefox", "en", detected="ar", prob=0.4))
    assert interface.transcribe(speech_audio) == ("Open Firefox", "en")


def test_prompt_echo_is_treated_as_silence(monkeypatch, speech_audio):
    use_model(monkeypatch, FakeModel(vocabulary.prompt_for(None), "en"))
    assert interface.transcribe_detailed(speech_audio).reason == "silence"


def test_short_command_inside_the_prompt_is_not_an_echo():
    assert not metrics.is_prompt_echo("Open Firefox", vocabulary.prompt_for(None))
    assert metrics.is_prompt_echo(vocabulary.PROMPT_EN, vocabulary.prompt_for(None))


# ---------- audio preprocessing ----------
def test_quiet_audio_is_amplified():
    quiet_speech = np.sin(np.linspace(0, 200, SAMPLE_RATE)).astype(np.float32) * 0.05
    out = audio_utils.normalize_gain(quiet_speech)
    assert 0.8 < float(np.max(np.abs(out))) <= 1.0


def test_loud_and_silent_audio_are_left_alone():
    loud_audio = np.full(1000, 0.7, dtype=np.float32)
    assert np.array_equal(audio_utils.normalize_gain(loud_audio), loud_audio)
    zeros = np.zeros(1000, dtype=np.float32)
    assert np.array_equal(audio_utils.normalize_gain(zeros), zeros)


def test_trim_silence_keeps_speech_and_cuts_the_edges():
    audio = np.concatenate(quiet(30) + loud(10) + quiet(30))      # 7 s total, 1 s speech
    out = audio_utils.trim_silence(audio)
    assert len(out) < len(audio) // 2
    assert float(np.max(np.abs(out))) == pytest.approx(0.1)


def test_dc_offset_is_removed():
    audio = np.full(1000, 0.3, dtype=np.float32) + np.sin(np.arange(1000)).astype(np.float32) * 0.1
    assert abs(float(np.mean(audio_utils.remove_dc(audio)))) < 1e-6


# ---------- metrics ----------
def test_normalize_unifies_arabic_forms_and_punctuation():
    assert metrics.normalize("\u0623\u0641\u062a\u062d \u0641\u0627\u064a\u0631\u0641\u0648\u0643\u0633.") == AR_OPEN_FIREFOX
    assert metrics.normalize("Open  Firefox!") == "open firefox"


def test_wer():
    assert metrics.wer("open firefox", "Open Firefox.") == 0.0
    assert metrics.wer("open firefox", "open") == 0.5
    assert metrics.wer("show my files", "show me files please") == pytest.approx(2 / 3)
    assert metrics.wer("", "") == 0.0
