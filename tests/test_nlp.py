# tests/test_nlp.py
# Run from the repo root:  pytest tests/test_nlp.py -v
import pytest
from nlp.understanding import understand, keyword_fallback, check_multiple_commands

KEYS = {"text", "language", "intent", "params", "confidence",
        "method", "needs_confirmation", "missing"}


# --------------------------------------------------------------------------
# The 9 spec phrases (English + Arabic): intent and parameters
# --------------------------------------------------------------------------
SPEC_CASES = [
    # text, language, intent, expected params
    ("Show my files", "en", "LIST_FILES", {}),
    ("اعرض ملفاتي", "ar", "LIST_FILES", {}),
    ("Create a file called notes", "en", "CREATE_FILE", {"name": "notes"}),
    ("انشئ ملف اسمه notes", "ar", "CREATE_FILE", {"name": "notes"}),
    ("Create a folder called Project", "en", "CREATE_FOLDER", {"name": "Project"}),
    ("انشئ مجلد اسمه Project", "ar", "CREATE_FOLDER", {"name": "Project"}),
    ("Rename notes to report", "en", "RENAME_FILE", {"name": "notes", "new_name": "report"}),
    ("غير اسم notes الى report", "ar", "RENAME_FILE", {"name": "notes", "new_name": "report"}),
    ("Delete report", "en", "DELETE_FILE", {"name": "report"}),
    ("احذف report", "ar", "DELETE_FILE", {"name": "report"}),
    ("Open Firefox", "en", "OPEN_APPLICATION", {"app": "firefox"}),
    ("افتح فايرفوكس", "ar", "OPEN_APPLICATION", {"app": "firefox"}),
    ("Close Firefox", "en", "CLOSE_APPLICATION", {"app": "firefox"}),
    ("اغلق فايرفوكس", "ar", "CLOSE_APPLICATION", {"app": "firefox"}),
    ("Show running processes", "en", "SHOW_PROCESSES", {}),
    ("اعرض العمليات", "ar", "SHOW_PROCESSES", {}),
    ("How much memory is used?", "en", "SHOW_SYSTEM_USAGE", {"resource": "ram"}),
    ("كم الذاكرة المستخدمة", "ar", "SHOW_SYSTEM_USAGE", {"resource": "ram"}),
]


def test_spec_phrases():
    for text, lang, intent, params in SPEC_CASES:
        r = understand(text, lang)
        assert r["intent"] == intent, text
        assert r["params"] == params, text
        assert r["missing"] == [], text
        assert r["confidence"] > 0.0, text


def test_output_shape_is_always_complete():
    for text in ("Show my files", "", "open firefox and delete report",
                 "What is the weather today"):
        r = understand(text, "en")
        assert KEYS <= set(r), text
        assert r["method"] in ("semantic", "keyword", "guard_rejected", "none")


def test_language_is_returned_and_auto_detected():
    assert understand("Show my files", "en")["language"] == "en"
    assert understand("اعرض ملفاتي", "ar")["language"] == "ar"
    assert understand("اعرض ملفاتي", "auto")["language"] == "ar"
    assert understand("Show my files", None)["language"] == "en"


# --------------------------------------------------------------------------
# Week 4: system usage (cpu / ram / disk) and processes, EN + AR
# --------------------------------------------------------------------------
USAGE_CASES = [
    ("how much memory is used", "ram"), ("show ram", "ram"), ("اعرض الرام", "ram"),
    ("what is my cpu usage", "cpu"), ("check cpu", "cpu"), ("اعرض المعالج", "cpu"),
    ("ايه استخدام المعالج", "cpu"),
    ("how much disk space is left", "disk"), ("how much storage do i have", "disk"),
    ("كم المساحة المتبقية على القرص", "disk"),
]


def test_system_usage_resources():
    for text, resource in USAGE_CASES:
        r = understand(text)
        assert r["intent"] == "SHOW_SYSTEM_USAGE", text
        assert r["params"] == {"resource": resource}, text


def test_system_usage_without_resource_asks_for_it():
    r = understand("show system usage", "en")
    assert r["intent"] == "SHOW_SYSTEM_USAGE"
    assert r["missing"] == ["resource"]


def test_process_paraphrases():
    for text in ("show tasks", "list processes", "اعرض العمليات الجارية",
                 "اعرض البرامج المفتوحة", "اعرض البرامج الشغالة"):
        assert understand(text)["intent"] == "SHOW_PROCESSES", text


# --------------------------------------------------------------------------
# Week 4: colloquial Arabic and extra English phrasings
# --------------------------------------------------------------------------
def test_colloquial_arabic_list_files():
    for text in ("شوفلي الملفات", "وريني الملفات", "هات الملفات"):
        assert understand(text, "ar")["intent"] == "LIST_FILES", text


def test_arabic_app_variants():
    cases = [("افتح المتصفح", "OPEN_APPLICATION", "firefox"),
             ("شغل الحاسبة", "OPEN_APPLICATION", "gnome-calculator"),
             ("اغلق الحاسبه", "CLOSE_APPLICATION", "gnome-calculator"),   # ة / ه
             ("اقفل التيرمينال", "CLOSE_APPLICATION", "gnome-terminal"),
             ("افتح محرر النصوص", "OPEN_APPLICATION", "gedit")]
    for text, intent, app in cases:
        r = understand(text, "ar")
        assert (r["intent"], r["params"].get("app")) == (intent, app), text


def test_english_polite_and_program_names():
    assert understand("can you list my files", "en")["intent"] == "LIST_FILES"
    assert understand("open firefox please", "en")["params"]["app"] == "firefox"
    assert understand("open gedit", "en")["params"]["app"] == "gedit"
    assert understand("open nautilus", "en")["params"]["app"] == "nautilus"


def test_arabic_file_name_is_kept():
    assert understand("انشئ ملف اسمه تقرير", "ar")["params"] == {"name": "تقرير"}
    assert understand("Delete notes.txt", "en")["params"] == {"name": "notes.txt"}


# --------------------------------------------------------------------------
# Confirmation and missing parameters
# --------------------------------------------------------------------------
def test_confirmation_flags():
    assert understand("Close firefox", "en")["needs_confirmation"] is True
    assert understand("Delete report", "en")["needs_confirmation"] is True
    assert understand("Open firefox", "en")["needs_confirmation"] is False
    assert understand("Show my files", "en")["needs_confirmation"] is False


def test_missing_parameters_are_listed():
    cases = [("create a file", "name"), ("create a folder", "name"),
             ("open", "app"), ("افتح", "app"), ("rename notes", "new_name"),
             ("open chrome", "app")]            # not on the allow-list
    for text, key in cases:
        r = understand(text)
        assert key in r["missing"], text
        assert key not in r["params"], text


# --------------------------------------------------------------------------
# Unsupported input
# --------------------------------------------------------------------------
def test_unsupported_phrases_are_unknown():
    for text in ("What is the weather today", "ما هو الطقس اليوم", "tell me a joke",
                 "show me the time", "اعرض الوقت", "shutdown", "اطفئ الجهاز"):
        r = understand(text)
        assert r["intent"] == "UNKNOWN", text
        assert r["needs_confirmation"] is False


def test_empty_and_blank_input():
    for text in ("", "   ", None):
        r = understand(text, "en")
        assert r["intent"] == "UNKNOWN"
        assert r["confidence"] == 0.0


# --------------------------------------------------------------------------
# Multiple-command guard
# --------------------------------------------------------------------------
def test_multiple_commands_guard():
    for text in ("open firefox and delete report", "افتح فايرفوكس و احذف الملف",
                 "open firefox then close it", "delete file; ls",
                 "open firefox & close terminal"):
        r = understand(text)
        assert r["intent"] == "UNKNOWN", text
        assert r["method"] == "guard_rejected", text
    assert check_multiple_commands("show my files") is False


# --------------------------------------------------------------------------
# Security: nothing is ever guessed or passed through as a command
# --------------------------------------------------------------------------
def test_mass_delete_never_gets_a_name():
    for text in ("delete all files", "delete all my files", "delete everything",
                 "remove everything", "احذف كل الملفات", "احذف كل شيء",
                 "احذف الكل"):
        r = understand(text)
        assert r["intent"] == "DELETE_FILE", text
        assert r["params"] == {}, text
        assert r["missing"] == ["name"], text
        assert r["needs_confirmation"] is True, text


def test_option_like_and_path_names_are_rejected():
    for text in ("rm -rf /", "delete -rf", "create a file called -n",
                 "create a file called ..", "delete ~", "create a file called a/b"):
        r = understand(text)
        assert "name" not in r["params"], text


def test_shell_text_is_never_executed_as_is():
    # understand() only returns a known intent plus parameters; it never
    # returns the raw sentence as something to run.
    r = understand("rm -rf /", "en")
    assert r["intent"] in ("DELETE_FILE", "UNKNOWN")
    assert "-rf" not in r["params"].values()


def test_keyword_confidence_is_capped():
    for text, _, _, _ in SPEC_CASES:
        _, conf = keyword_fallback(text)
        assert conf <= 0.80, text


# --------------------------------------------------------------------------
# Semantic matcher: measured separately (skipped if the model is missing).
# Prints the accuracy so you can tune SEMANTIC_THRESHOLD (0.55) in the report.
# --------------------------------------------------------------------------
PARAPHRASES = [
    ("could you show me what files i have", "LIST_FILES"),
    ("what is inside my folder", "LIST_FILES"),
    ("ايه الملفات اللي عندي", "LIST_FILES"),
    ("i need a new empty file", "CREATE_FILE"),
    ("make me a new directory", "CREATE_FOLDER"),
    ("get rid of the file", "DELETE_FILE"),
    ("امسح الملف", "DELETE_FILE"),
    ("launch the web browser", "OPEN_APPLICATION"),
    ("شغل المتصفح", "OPEN_APPLICATION"),
    ("shut the browser", "CLOSE_APPLICATION"),
    ("what programs are running", "SHOW_PROCESSES"),
    ("how much ram am i using", "SHOW_SYSTEM_USAGE"),
    ("كم المساحة الفاضية", "SHOW_SYSTEM_USAGE"),
]
REJECTED = ["what is the weather today", "ما هو الطقس اليوم", "tell me a joke",
            "who won the match", "play some music", "send an email"]


def test_semantic_matcher_accuracy():
    pytest.importorskip("sentence_transformers")
    from nlp.understanding import semantic_match, get_model
    if get_model() is None:
        pytest.skip("sentence-transformers model could not be loaded")

    correct = 0
    for text, intent in PARAPHRASES:
        m = semantic_match(text)
        correct += bool(m and m[0] == intent)
    wrongly_accepted = [t for t in REJECTED if semantic_match(t) is not None]

    print(f"\nsemantic accuracy: {correct}/{len(PARAPHRASES)}; "
          f"unsupported wrongly accepted: {wrongly_accepted}")
    assert correct / len(PARAPHRASES) >= 0.75
    assert len(wrongly_accepted) <= 1
