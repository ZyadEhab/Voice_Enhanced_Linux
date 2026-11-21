"""
Voice-Enhanced Linux - Modern Flet Entry Point (main_flet.py)
Runs the modern Flet desktop UI on top of the exact same verified backend pipeline.
"""
import inspect
import re
import sys
import threading
from types import SimpleNamespace
import flet as ft

import main as backend_main
from gui_flet.app import ModernVoiceApp
from main import VoicePipelineController, init_safe_workspace, prewarm_models
from tts.speaker import speak

_CHIP_LOCK = threading.Lock()


def _detect_stt_return(cmd_text: str, language: str, call_src: str):
    """Match whatever return structure VoicePipelineController expects from STT."""
    if re.search(r'\[\s*["\']text["\']\s*\]|\.get\(\s*["\']text["\']', call_src):
        return {"text": cmd_text, "language": language, "confidence": 1.0}
    if ".text" in call_src:
        return SimpleNamespace(text=cmd_text, language=language, confidence=1.0)
    # Check tuple unpacking (e.g., text, lang = ... or text, lang, conf = ...)
    for line in call_src.splitlines():
        s = line.strip()
        if "=" in s and not s.startswith("#") and "==" not in s:
            lhs = s.split("=", 1)[0]
            rhs = s.split("=", 1)[1]
            if "," in lhs and any(k in rhs.lower() for k in ("stt", "transcri", "whisper", "recogni", "speech", "listen")):
                n_vars = len([p for p in lhs.split(",") if p.strip()])
                if n_vars == 3:
                    return (cmd_text, language, 1.0)
                return (cmd_text, language)
    return cmd_text


def make_text_pipeline(controller: VoicePipelineController):
    """Run VoicePipelineController using a quick-chip text command without opening the mic."""
    try:
        call_src = inspect.getsource(VoicePipelineController)
    except Exception:
        call_src = ""

    def _run(emit, cmd_text: str, language: str, confirm) -> None:
        with _CHIP_LOCK:
            stub_result = _detect_stt_return(cmd_text, language, call_src)
            patched = []

            def _fake_stt(*args, **kwargs):
                return stub_result

            def _fake_audio(*args, **kwargs):
                return b"\x00" * 3200

            def _patch_container(container):
                try:
                    items = list(vars(container).items())
                except TypeError:
                    return
                for attr_name, obj in items:
                    if isinstance(obj, type) or attr_name.startswith("__"):
                        continue
                    mod_origin = getattr(obj, "__module__", "") or getattr(type(obj), "__module__", "")
                    if callable(obj) and (mod_origin == "stt" or mod_origin.startswith("stt.")):
                        patched.append((container, attr_name, obj))
                        setattr(container, attr_name, _fake_stt)
                    elif callable(obj) and (mod_origin == "audio" or mod_origin.startswith("audio.")):
                        patched.append((container, attr_name, obj))
                        setattr(container, attr_name, _fake_audio)
                    elif mod_origin == "stt" or mod_origin.startswith("stt."):
                        # Instance object (e.g. self.stt): patch its public methods
                        for m_name in dir(obj):
                            if m_name.startswith("_"):
                                continue
                            m_val = getattr(obj, m_name, None)
                            if callable(m_val):
                                patched.append((obj, m_name, m_val))
                                setattr(obj, m_name, _fake_stt)
                    elif mod_origin == "audio" or mod_origin.startswith("audio."):
                        for m_name in dir(obj):
                            if m_name.startswith("_"):
                                continue
                            m_val = getattr(obj, m_name, None)
                            if callable(m_val):
                                patched.append((obj, m_name, m_val))
                                setattr(obj, m_name, _fake_audio)

            _patch_container(backend_main)
            _patch_container(controller)
            for mod_name, mod in list(sys.modules.items()):
                if mod is not None and (mod_name == "stt" or mod_name.startswith("stt.") or mod_name == "audio" or mod_name.startswith("audio.")):
                    _patch_container(mod)

            try:
                controller(emit, language, confirm)
            finally:
                for target, attr_name, orig_obj in reversed(patched):
                    setattr(target, attr_name, orig_obj)

    return _run


def main(page: ft.Page) -> None:
    ws = init_safe_workspace()
    controller = VoicePipelineController()
    ModernVoiceApp(
        page=page,
        pipeline=controller,
        text_pipeline=make_text_pipeline(controller),
        speak_fn=speak,
        workspace=str(ws),
        model_name="faster-whisper (small)",
    )


if __name__ == "__main__":
    print("=== Voice-Enhanced Linux (Modern Flet UI) ===")
    ws = init_safe_workspace()
    print(f"[System] Safe workspace ready at: {ws} (mode {oct(ws.stat().st_mode & 0o777)})")
    prewarm_models()
    if hasattr(ft, "run"):
        ft.run(main)
    else:
        ft.app(target=main)
