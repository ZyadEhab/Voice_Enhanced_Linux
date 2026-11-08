"""
stt/metrics.py  --  Helpers to measure STT accuracy (used by stt/evaluate.py and the transcriber).

normalize() is ONLY for comparing texts here. It does not change what transcribe()
returns: the NLP module still owns the real normalization of commands.
"""
import re

_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670\u0640]")     # tashkeel + tatweel
_LETTERS = str.maketrans("أإآىة", "ااايه")                    # unify Arabic letter forms
ECHO_MIN_CHARS = 40       # a real command is shorter than this; a leaked prompt is longer


def normalize(text: str) -> str:
    text = _DIACRITICS.sub("", text.lower()).translate(_LETTERS)
    return " ".join(re.sub(r"[^\w\s]", " ", text).split())


def wer(reference: str, hypothesis: str) -> float:
    """Word error rate on normalized text: (substitutions + deletions + insertions) / reference words."""
    ref, hyp = normalize(reference).split(), normalize(hypothesis).split()
    if not ref:
        return 0.0 if not hyp else 1.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cost = 0 if r == h else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1] / len(ref)


def is_prompt_echo(text: str, prompt: str) -> bool:
    """Whisper sometimes 'transcribes' its own prompt when the audio is noise. Detect that."""
    norm_text = normalize(text)
    return len(norm_text) >= ECHO_MIN_CHARS and norm_text in normalize(prompt)
