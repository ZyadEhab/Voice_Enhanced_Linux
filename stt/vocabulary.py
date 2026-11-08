"""
stt/vocabulary.py  --  Words the system really understands, in English and Arabic.

Why it exists (Task 3): the validation layer only accepts a fixed allow-list of
intents, applications and resources (PROJECT_CONTEXT Sections 5, 5.1, 5.2).
Whisper makes most mistakes on exactly those words (firefox, gnome-terminal,
"mkdir"-style names, Arabic app names), so we hint them to the model through
`initial_prompt`.  If you change the allow-lists, change this file in the same pull request.
"""
from typing import Optional

PROMPT_EN = (
    "Voice commands: show my files, create a file called, create a folder called, "
    "rename, delete, open Firefox, close Firefox, terminal, calculator, text editor, "
    "show running processes, how much memory, CPU, disk usage."
)

PROMPT_AR = (
    "أوامر صوتية: اعرض ملفاتي، انشئ ملف اسمه، انشئ مجلد اسمه، غير اسم، احذف، "
    "افتح فايرفوكس، اغلق فايرفوكس، المتصفح، التيرمينال، الحاسبة، محرر النصوص، "
    "اعرض العمليات، كم الذاكرة المستخدمة، المعالج، القرص."
)


def prompt_for(language: Optional[str]) -> str:
    """Prompt for a forced language, or the bilingual one when the language is auto-detected."""
    if language == "en":
        return PROMPT_EN
    if language == "ar":
        return PROMPT_AR
    return PROMPT_EN + " " + PROMPT_AR


# (language, exactly what the speaker should say). Used by stt/evaluate.py.
# The last pair in each language is an unsupported command the validator must reject.
COMMANDS = [
    ("en", "Show my files"),
    ("en", "Create a file called notes"),
    ("en", "Create a folder called Project"),
    ("en", "Rename notes to report"),
    ("en", "Delete report"),
    ("en", "Open Firefox"),
    ("en", "Close Firefox"),
    ("en", "Show running processes"),
    ("en", "How much memory is used"),
    ("en", "What is the weather today"),
    ("ar", "اعرض ملفاتي"),
    ("ar", "انشئ ملف اسمه notes"),
    ("ar", "انشئ مجلد اسمه Project"),
    ("ar", "غير اسم notes الى report"),
    ("ar", "احذف report"),
    ("ar", "افتح فايرفوكس"),
    ("ar", "اغلق فايرفوكس"),
    ("ar", "اعرض العمليات"),
    ("ar", "كم الذاكرة المستخدمة"),
    ("ar", "ما هو الطقس اليوم"),
]
