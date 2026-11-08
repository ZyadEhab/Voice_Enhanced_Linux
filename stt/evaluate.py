"""
stt/evaluate.py  --  Measure STT accuracy and compare the Task 3 improvements fairly.

  python3 -m stt.evaluate --record            # say the 20 commands once -> stt_samples/*.wav + manifest.csv
  python3 -m stt.evaluate --record --repeat 2 # two takes of each command (more reliable numbers)
  python3 -m stt.evaluate --run               # same audio through every setting -> docs/stt_accuracy.md

Every setting is tested on the SAME recordings, so differences come from the setting,
not from how you spoke that day. Record in the conditions of the demo (same room, same mic).
"""
import argparse
import csv
import os
import time
import wave

import numpy as np

from .interface import SAMPLE_RATE
from .metrics import normalize, wer
from .transcriber import Settings, transcribe_detailed
from .vocabulary import COMMANDS

SAMPLES_DIR = "stt_samples"
MANIFEST = os.path.join(SAMPLES_DIR, "manifest.csv")
REPORT = os.path.join("docs", "stt_accuracy.md")

# name -> (Settings, pass the expected language as a hint?)
CONFIGS = {
    "baseline":          (Settings(False, False, False), False),
    "+prompt":           (Settings(True, False, False), False),
    "+preprocess":       (Settings(False, True, False), False),
    "+lang fallback":    (Settings(False, False, True), False),
    "all":               (Settings(True, True, True), False),
    "all + lang hint":   (Settings(True, True, True), True),
}


def save_wav(path: str, audio: np.ndarray) -> None:
    data = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(data.tobytes())


def load_wav(path: str) -> np.ndarray:
    with wave.open(path, "rb") as w:
        raw = w.readframes(w.getnframes())
    return (np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0)


def record_samples(repeat: int, only: str) -> None:
    from .recorder import record
    os.makedirs(SAMPLES_DIR, exist_ok=True)
    new_file = not os.path.exists(MANIFEST)
    with open(MANIFEST, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["file", "language", "expected"])
        for take in range(1, repeat + 1):
            for idx, (lang, expected) in enumerate(COMMANDS):
                if only and lang != only:
                    continue
                input(f"\n[{lang}] take {take}: say \"{expected}\"   [Enter to start] ")
                print("  Listening...")
                audio = record()
                name = f"{idx:02d}_{lang}_t{take}.wav"
                save_wav(os.path.join(SAMPLES_DIR, name), audio)
                writer.writerow([name, lang, expected])
                f.flush()
                print(f"  saved {name} ({len(audio) / SAMPLE_RATE:.1f}s)")
    print(f"\nDone. Now run: python3 -m stt.evaluate --run")


def load_manifest():
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_evaluation() -> None:
    rows = load_manifest()
    if not rows:
        print("No samples. Run with --record first.")
        return
    audios = {r["file"]: load_wav(os.path.join(SAMPLES_DIR, r["file"])) for r in rows}

    results = {}   # config -> list of dicts
    for name, (settings, use_hint) in CONFIGS.items():
        print(f"\n== {name} ==")
        out = []
        for r in rows:
            t0 = time.time()
            res = transcribe_detailed(audios[r["file"]],
                                      r["language"] if use_hint else None, settings)
            secs = time.time() - t0
            exact = normalize(res.text) == normalize(r["expected"])
            out.append({"lang": r["language"], "expected": r["expected"], "text": res.text,
                        "detected": res.language, "exact": exact,
                        "wer": wer(r["expected"], res.text), "secs": secs})
            print(f"  {'OK ' if exact else 'ERR'} [{res.language or '-':>2}] {res.text}")
        results[name] = out

    os.makedirs("docs", exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(f"# STT accuracy ({len(rows)} recordings)\n\n")
        f.write("| Setting | Exact EN | Exact AR | WER EN | WER AR | Language correct | Avg seconds |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for name, out in results.items():
            f.write("| " + name + " | " + " | ".join(summarize(out)) + " |\n")
        f.write("\n## Per recording\n\n")
        names = list(results)
        f.write("| Expected | " + " | ".join(names) + " |\n")
        f.write("|---|" + "---|" * len(names) + "\n")
        for i, r in enumerate(rows):
            cells = [("OK: " if results[n][i]["exact"] else "ERR: ") + (results[n][i]["text"] or "(empty)")
                     for n in names]
            f.write(f"| {r['expected']} | " + " | ".join(cells) + " |\n")
    print(f"\nSaved {REPORT}")


def summarize(out):
    def pct(items, key):
        return f"{100 * sum(1 for x in items if x[key]) / len(items):.0f}%" if items else "-"

    def mean_wer(items):
        return f"{100 * sum(x['wer'] for x in items) / len(items):.0f}%" if items else "-"

    en = [x for x in out if x["lang"] == "en"]
    ar = [x for x in out if x["lang"] == "ar"]
    lang_ok = f"{100 * sum(1 for x in out if x['detected'] == x['lang']) / len(out):.0f}%"
    avg = f"{sum(x['secs'] for x in out) / len(out):.1f}"
    return [pct(en, "exact"), pct(ar, "exact"), mean_wer(en), mean_wer(ar), lang_ok, avg]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true", help="record the command samples")
    parser.add_argument("--run", action="store_true", help="compare all settings on the samples")
    parser.add_argument("--repeat", type=int, default=1, help="takes per command when recording")
    parser.add_argument("--only", choices=["en", "ar"], default="", help="record one language only")
    args = parser.parse_args()
    if args.record:
        record_samples(args.repeat, args.only)
    elif args.run:
        run_evaluation()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
