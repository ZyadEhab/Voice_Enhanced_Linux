"""Correct Arabic display in Tkinter (open decision #8 in PROJECT_CONTEXT.md).

Tk on Linux does not join Arabic letters or reorder right-to-left text by itself.
arabic-reshaper joins the letters; python-bidi puts them in visual order.
If the libraries are missing the text is returned unchanged, so the GUI still runs.

Only use shape() for DISPLAY. Never send shaped text to TTS or to the NLP module.
"""
from __future__ import annotations

import re

try:  # optional dependencies (pip install arabic-reshaper python-bidi)
    import arabic_reshaper
    from bidi.algorithm import get_display
    AVAILABLE = True
except ImportError:  # pragma: no cover - depends on the machine
    AVAILABLE = False

_ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F]")


def has_arabic(text: str) -> bool:
    return bool(_ARABIC.search(text or ""))


def shape(text: str) -> str:
    """Return `text` ready to show in a Tk widget. Non-Arabic text is untouched."""
    if not text or not has_arabic(text) or not AVAILABLE:
        return text or ""
    # Shape line by line so multi-line results keep their line breaks.
    return "\n".join(get_display(arabic_reshaper.reshape(line)) for line in text.split("\n"))
