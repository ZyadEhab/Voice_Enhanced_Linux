"""
stt/demo.py  --  Try the first STT prototype with your real microphone.

  python3 -m stt.demo            # free mode: speak, see text + language, repeat (Ctrl+C to quit)
  python3 -m stt.demo --table    # guided test: 3 English + 3 Arabic commands -> docs/stt_test_results.md
"""
import argparse
import os
import re
import time

from . import MicrophoneError, TranscriptionError, record, transcribe_detailed

TEST_COMMANDS = [
    ("en", "Show my files"),
    ("en", "Open Firefox"),
    ("en", "How much memory is used"),
    ("ar", "اعرض ملفاتي"),
    ("ar", "افتح فايرفوكس"),
    ("ar", "كم الذاكرة المستخدمة"),
]


def _norm(text: str) -> str:
    """Loose comparison only for this demo (the NLP module owns real normalization)."""
    text = text.lower()
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)            # Arabic diacritics
    text = text.translate(str.maketrans("أإآىة", "ااايه"))        # unify letter forms
    return " ".join(re.sub(r"[^\w\s]", " ", text).split())


def listen_once():
    print("  Listening... speak now")
    t0 = time.time()
    audio = record(on_speech_start=lambda: print("  (speech detected)"))
    t1 = time.time()
    print("  Transcribing... (first run loads the model, it can take a while)")
    result = transcribe_detailed(audio)
    t2 = time.time()
    print(f"  recorded {result.duration_s:.1f}s | record {t1 - t0:.1f}s | transcribe {t2 - t1:.1f}s")
    return result


def free_mode():
    print("Press Enter, then speak a command. Ctrl+C to quit.")
    while True:
        input("\n[Enter] to listen > ")
        result = listen_once()
        if result.text:
            prob = f"{result.language_probability:.2f}" if result.language_probability else "?"
            print(f"  TEXT: {result.text}\n  LANGUAGE: {result.language} (confidence {prob})")
        else:
            print(f"  No text ({result.reason}). Please repeat.")


def table_mode():
    rows = []
    for lang, expected in TEST_COMMANDS:
        input(f"\nSay ({lang}): \"{expected}\"   [Enter to start] ")
        result = listen_once()
        recognized = result.text or f"(empty: {result.reason})"
        verdict = "Pass" if _norm(result.text) == _norm(expected) else "Check"
        print(f"  -> {recognized}  [{verdict}]")
        rows.append((lang, expected, recognized, result.language or "-", verdict))

    os.makedirs("docs", exist_ok=True)
    path = os.path.join("docs", "stt_test_results.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("| # | Language | Spoken command | Recognized text | Detected | Result |\n")
        f.write("|---|---|---|---|---|---|\n")
        for i, (lang, exp, rec, det, verdict) in enumerate(rows, 1):
            f.write(f"| {i} | {lang} | {exp} | {rec} | {det} | {verdict} |\n")
    print(f"\nSaved {path}. 'Check' = not an exact match: review it by hand and edit the table.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", action="store_true", help="run the guided 3 EN + 3 AR test")
    args = parser.parse_args()
    try:
        table_mode() if args.table else free_mode()
    except MicrophoneError as exc:
        print(f"Microphone problem: {exc}")
    except TranscriptionError as exc:
        print(f"Speech recognition problem: {exc}")
    except KeyboardInterrupt:
        print("\nBye")


if __name__ == "__main__":
    main()
