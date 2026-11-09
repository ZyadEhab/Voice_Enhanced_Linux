import re

try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:  # keyword fallback keeps working without the library
    SentenceTransformer = None
    util = None

from nlp.intents import (
    SUPPORTED_INTENTS, ALLOWED_APPS, ALLOWED_RESOURCES, CONFIRMATION_INTENTS,
    FALLBACK_RULES, NAME_MARKERS, RENAME_SEPARATORS, STOPWORDS, NAME_FILLER,
    BLOCKED_NAMES, CONJUNCTION_WORDS, CONJUNCTION_PHRASES, CONJUNCTION_CHARS,
)

# نموذج paraphrase-multilingual-MiniLM-L12-v2 يدعم العربية والإنجليزية بكفاءة
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

SEMANTIC_THRESHOLD = 0.55        # minimum cosine similarity (per the spec)
SEMANTIC_MARGIN = 0.03           # best intent must beat the runner-up by this much
KEYWORD_CONFIDENCE_CAP = 0.80    # keyword matches never exceed this (per the spec)

# Values allowed in the "method" field. Agree on this list with the team.
METHOD_SEMANTIC = "semantic"
METHOD_KEYWORD = "keyword"
METHOD_GUARD = "guard_rejected"
METHOD_NONE = "none"             # empty input, or nothing matched at all
ALLOWED_METHODS = (METHOD_SEMANTIC, METHOD_KEYWORD, METHOD_GUARD, METHOD_NONE)

_model = None
_model_load_attempted = False
_phrase_index = None             # (phrases, intents, embeddings), built once


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
def normalize_text(text: str) -> str:
    """معالجة وتطبيع النص: توحيد الحروف، إزالة التشكيل وعلامات الترقيم"""
    if not text:
        return ""
    text = text.lower().strip()
    # إزالة التشكيل العربي والتطويل
    text = re.sub(r'[\u064b-\u0652\u0640]', '', text)
    # توحيد أشكال الهمزات والألفات (أ إ آ -> ا)
    text = re.sub(r'[أإآ]', 'ا', text)
    # توحيد التاء المربوطة والهاء (ة -> ه) و(ى -> ي)
    text = text.replace('ة', 'ه').replace('ى', 'ي')
    # إزالة علامات الترقيم الزائدة
    text = re.sub(r'[^\w\s]', '', text)
    return text


def _tokens(text: str) -> list:
    return normalize_text(text).split()


def _ncue(cue: str) -> tuple:
    """Normalize a cue string into a tuple of tokens."""
    return tuple(normalize_text(cue).split())


def _has_cue(tokens: list, cue: tuple) -> bool:
    """True if `cue` appears in `tokens` as a run of WHOLE words."""
    size = len(cue)
    if size == 0 or size > len(tokens):
        return False
    cue = list(cue)
    return any(tokens[i:i + size] == cue for i in range(len(tokens) - size + 1))


def _find_cue(tokens: list, cues: list):
    """Longest cue from `cues` found in `tokens`, or None."""
    best = None
    for cue in cues:
        if _has_cue(tokens, cue) and (best is None or len(cue) > len(best)):
            best = cue
    return best


def _lookup(tokens: list, keyed: list):
    """Value of the earliest whole-word match; longest key wins on a tie.
    `keyed` is a list of (cue_tuple, value) sorted longest cue first."""
    for i in range(len(tokens)):
        for cue, value in keyed:
            if tokens[i:i + len(cue)] == list(cue):
                return value
    return None


def detect_language(text: str) -> str:
    """'ar' if the text is mostly Arabic letters, otherwise 'en'."""
    arabic = len(re.findall(r'[\u0600-\u06FF]', text or ""))
    latin = len(re.findall(r'[A-Za-z]', text or ""))
    return "ar" if arabic > latin else "en"


def _resolve_language(text: str, language) -> str:
    code = str(language or "").lower()[:2]
    return code if code in ("en", "ar") else detect_language(text)


# ---------------------------------------------------------------------------
# Pre-built lookup tables (normalized once at import time)
# ---------------------------------------------------------------------------
_PHRASES = [
    (intent, _ncue(phrase))
    for intent, data in SUPPORTED_INTENTS.items()
    for phrases in data.values()
    for phrase in phrases
    if _ncue(phrase)
]

_RULES = {
    intent: {
        "verbs": [c for c in map(_ncue, rule["verbs"]) if c],
        "nouns": [c for c in map(_ncue, rule["nouns"]) if c],
        "need_verb": rule["need_verb"],
        "need_noun": rule["need_noun"],
    }
    for intent, rule in FALLBACK_RULES.items()
}

_APP_KEYS = sorted(((_ncue(k), v) for k, v in ALLOWED_APPS.items() if _ncue(k)),
                   key=lambda kv: -len(kv[0]))
_RESOURCE_KEYS = sorted(((_ncue(k), v) for k, v in ALLOWED_RESOURCES.items() if _ncue(k)),
                        key=lambda kv: -len(kv[0]))

_STOP = {normalize_text(w) for w in STOPWORDS}
_NAME_MARKERS = {normalize_text(w) for w in NAME_MARKERS}
_RENAME_SEPARATORS = {normalize_text(w) for w in RENAME_SEPARATORS}
_BLOCKED_NAMES = {normalize_text(w) for w in BLOCKED_NAMES}
_NAME_FILLER = {normalize_text(w) for w in NAME_FILLER}

_NAME_INTENTS = ("CREATE_FILE", "CREATE_FOLDER", "DELETE_FILE")
_FILE_INTENTS = _NAME_INTENTS + ("RENAME_FILE",)
# Command words of the file intents are skipped when looking for the name
_NAME_SKIP = _NAME_FILLER | {
    token
    for intent in _FILE_INTENTS
    for kind in ("verbs", "nouns")
    for cue in _RULES[intent][kind]
    for token in cue
}

_CONJ_WORDS = {normalize_text(w) for w in CONJUNCTION_WORDS}
_CONJ_PHRASES = [tuple(normalize_text(w) for w in p) for p in CONJUNCTION_PHRASES]

# kind of match -> base confidence. Coverage of the sentence adds up to +0.15.
_RANK_PHRASE, _RANK_BOTH, _RANK_VERB, _RANK_NOUN = 3, 2, 1, 0
_BASE_CONFIDENCE = {_RANK_PHRASE: 0.65, _RANK_BOTH: 0.55,
                    _RANK_VERB: 0.45, _RANK_NOUN: 0.40}


# ---------------------------------------------------------------------------
# Multi-command guard
# ---------------------------------------------------------------------------
def check_multiple_commands(text: str) -> bool:
    """حارس الأوامر المتعددة: رفض الجمل التي تحتوي على أكثر من أمر بربط الواو أو ثم"""
    if not text:
        return False
    if any(ch in text for ch in CONJUNCTION_CHARS):
        return True
    tokens = _tokens(text)          # lower-cased, so "AND" / "Then" are caught too
    if any(t in _CONJ_WORDS for t in tokens):
        return True
    return any(_has_cue(tokens, phrase) for phrase in _CONJ_PHRASES)


# ---------------------------------------------------------------------------
# Keyword fallback
# ---------------------------------------------------------------------------
def keyword_fallback(text: str):
    """الوضع الاحتياطي للكلمات المفتاحية في حال تعذر نموذج الذكاء الاصطناعي

    Whole-word matching only. Tries full example phrases first, then
    verb/noun rules. Returns (intent, confidence); confidence reflects the
    kind of match and how much of the sentence it explains (max 0.80).
    """
    tokens = _tokens(text)
    if not tokens:
        return "UNKNOWN", 0.0
    content = {t for t in tokens if t not in _STOP} or set(tokens)

    best = None  # (rank, matched_len, -order, intent, matched_tokens)

    for order, (intent, cue) in enumerate(_PHRASES):
        if _has_cue(tokens, cue):
            cand = (_RANK_PHRASE, len(cue), -order, intent, set(cue))
            if best is None or cand[:3] > best[:3]:
                best = cand

    for order, (intent, rule) in enumerate(_RULES.items()):
        verb = _find_cue(tokens, rule["verbs"])
        noun = _find_cue(tokens, rule["nouns"])
        if rule["need_verb"] and not verb:
            continue
        if rule["need_noun"] and not noun:
            continue
        if not verb and not noun:
            continue
        rank = _RANK_BOTH if (verb and noun) else (_RANK_VERB if verb else _RANK_NOUN)
        matched = (verb or ()) + (noun or ())
        cand = (rank, len(matched), -order, intent, set(matched))
        if best is None or cand[:3] > best[:3]:
            best = cand

    if best is None:
        return "UNKNOWN", 0.0

    rank, _, _, intent, matched_tokens = best
    coverage = len(matched_tokens & content) / len(content)
    confidence = _BASE_CONFIDENCE[rank] + 0.15 * coverage
    return intent, round(min(KEYWORD_CONFIDENCE_CAP, confidence), 2)


# ---------------------------------------------------------------------------
# Semantic matcher
# ---------------------------------------------------------------------------
def get_model():
    """Loads the model once. A failed load is NOT retried on every command."""
    global _model, _model_load_attempted
    if _model is not None or _model_load_attempted:
        return _model
    _model_load_attempted = True
    if SentenceTransformer is None:
        print("Warning: sentence-transformers is not installed; "
              "using the keyword fallback only.")
        return None
    try:
        _model = SentenceTransformer(MODEL_NAME)
    except Exception as e:
        print(f"Warning: Could not load transformer model: {e}")
        _model = None
    return _model


def _get_phrase_index(model):
    """Embeds every example phrase once and caches the result."""
    global _phrase_index
    if _phrase_index is None:
        phrases, intents = [], []
        for intent, data in SUPPORTED_INTENTS.items():
            for lang_phrases in data.values():
                for phrase in lang_phrases:
                    phrases.append(phrase)
                    intents.append(intent)
        embeddings = model.encode(phrases, convert_to_tensor=True)
        _phrase_index = (phrases, intents, embeddings)
    return _phrase_index


def warmup():
    """Call once at startup (e.g. from main.py) so the first command is fast."""
    model = get_model()
    if model is not None:
        try:
            _get_phrase_index(model)
        except Exception as e:
            print(f"Semantic warm-up error: {e}")


def semantic_match(text: str):
    """Returns (intent, confidence) or None if the matcher is unavailable,
    below the threshold, or the top two intents are too close to call."""
    model = get_model()
    if model is None:
        return None
    try:
        _, intents, embeddings = _get_phrase_index(model)
        query = model.encode(text, convert_to_tensor=True)
        scores = util.cos_sim(query, embeddings)[0].tolist()
    except Exception as e:
        print(f"Semantic matching error: {e}")
        return None

    best_per_intent = {}
    for score, intent in zip(scores, intents):
        if score > best_per_intent.get(intent, -1.0):
            best_per_intent[intent] = score
    ranked = sorted(best_per_intent.items(), key=lambda kv: kv[1], reverse=True)

    top_intent, top_score = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    if top_score < SEMANTIC_THRESHOLD or (top_score - runner_up) < SEMANTIC_MARGIN:
        return None
    return top_intent, round(top_score, 2)


# ---------------------------------------------------------------------------
# Parameter extraction
# ---------------------------------------------------------------------------
_LEADING = "\"'“‘([{«"
_TRAILING = ".,!?;:،؟؛\"'”’)]}»…"


def _name_tokens(text: str) -> list:
    """[(clean, normalized)] per word. Only the ends are trimmed, so inner dots
    survive ("notes.txt") while "notes." becomes "notes"."""
    out = []
    for raw in text.split():
        clean = raw.lstrip(_LEADING).rstrip(_TRAILING)
        norm = normalize_text(clean)
        if clean and norm:
            out.append((clean, norm))
    return out


def _is_safe_name(name) -> bool:
    if not name or len(name) > 255:
        return False
    if "/" in name or "\\" in name or "\x00" in name:
        return False
    if name in (".", "..") or any(ch in name for ch in "*?"):
        return False
    return normalize_text(name) not in _BLOCKED_NAMES


def _set_name(params: dict, missing: list, key: str, value):
    if value and _is_safe_name(value):
        params[key] = value
    else:
        missing.append(key)


def _extract_name(text: str):
    """Name for create / delete: the word after "called/named/اسمه", otherwise
    what is left once command words, fillers and punctuation are dropped."""
    toks = _name_tokens(text)
    for i, (_, norm) in enumerate(toks):
        if norm in _NAME_MARKERS:
            for clean, n in toks[i + 1:]:
                if n not in _NAME_FILLER:
                    return clean
            return None
    rest = [clean for clean, norm in toks if norm not in _NAME_SKIP]
    if not rest:
        return None
    # Paraphrases ("get rid of notes") leave extra words in front of the name,
    # so prefer something file-like ("notes.txt"), otherwise the last word left.
    dotted = [w for w in rest if "." in w]
    return dotted[0] if dotted else rest[-1]


def _extract_rename_names(text: str):
    """(old, new) for "rename notes to report" / "غير اسم الملف notes الى report"."""
    toks = _name_tokens(text)
    sep = next((i for i, (_, n) in enumerate(toks) if n in _RENAME_SEPARATORS), None)
    if sep is not None:
        before = [c for c, n in toks[:sep] if n not in _NAME_SKIP]
        after = [c for c, n in toks[sep + 1:] if n not in _NAME_FILLER]
        return (before[-1] if before else None), (after[0] if after else None)
    rest = [c for c, n in toks if n not in _NAME_SKIP]
    return (rest[0] if rest else None), (rest[1] if len(rest) > 1 else None)


def extract_parameters(intent: str, text: str):
    """استخراج المعلمات المطلوبة بناءً على النية (مثل اسم الملف أو التطبيق)

    Returns (params, missing). A parameter that cannot be found is listed in
    `missing` and left out of `params`; nothing is guessed.
    """
    params = {}
    missing = []

    if intent == "RENAME_FILE":
        old, new = _extract_rename_names(text)
        _set_name(params, missing, "name", old)
        _set_name(params, missing, "new_name", new)

    elif intent in _NAME_INTENTS:
        _set_name(params, missing, "name", _extract_name(text))

    elif intent in ("OPEN_APPLICATION", "CLOSE_APPLICATION"):
        app = _lookup(_tokens(text), _APP_KEYS)   # whole-word, normalized
        if app:
            params["app"] = app
        else:
            missing.append("app")

    elif intent == "SHOW_SYSTEM_USAGE":
        resource = _lookup(_tokens(text), _RESOURCE_KEYS)
        if resource:
            params["resource"] = resource
        else:
            missing.append("resource")

    return params, missing


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def _result(text, language, intent="UNKNOWN", params=None, confidence=0.0,
            method=METHOD_NONE, needs_confirmation=False, missing=None, error=None):
    """One place builds the output, so every path returns the same keys."""
    result = {
        "text": text,
        "language": language,
        "intent": intent,
        "params": params or {},
        "confidence": confidence,
        "method": method,
        "needs_confirmation": needs_confirmation,
        "missing": missing or [],
    }
    if error:
        result["error"] = error
    return result


def understand(text: str, language: str = "en") -> dict:
    """الدالة الرئيسية المطلوبة في عقد الواجهات للتحويل من نص إلى Intent منظم

    `language` is "en" or "ar" (anything else, e.g. "auto" or None, is detected
    from the text) and is always returned in the result.
    """
    language = _resolve_language(text, language)

    if not text or not text.strip():
        return _result(text or "", language)

    # 1. فحص الأوامر المتعددة المرفوضة
    if check_multiple_commands(text):
        return _result(text, language, method=METHOD_GUARD,
                       error="Multiple commands in one sentence are not allowed.")

    # 2. المطابقة الدلالية إذا كان النموذج متاحاً
    intent, confidence, method = "UNKNOWN", 0.0, METHOD_NONE
    match = semantic_match(text)
    if match is not None:
        intent, confidence = match
        method = METHOD_SEMANTIC
    else:
        # 3. الاحتياطي (Fallback): النموذج غير متاح أو الثقة ضعيفة
        intent, confidence = keyword_fallback(text)
        if intent != "UNKNOWN":
            method = METHOD_KEYWORD

    # 4. استخراج المعلمات
    params, missing = extract_parameters(intent, text)

    # 5. تحديد هل العملية تتطلب تأكيد (مثل الحذف أو إغلاق تطبيق)
    return _result(text, language, intent=intent, params=params,
                   confidence=confidence, method=method,
                   needs_confirmation=intent in CONFIRMATION_INTENTS,
                   missing=missing)