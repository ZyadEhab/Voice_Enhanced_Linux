# nlp/intents.py
#
# Data only: no logic lives here. nlp/nlp.py reads everything below.
#
#   SUPPORTED_INTENTS  full example sentences. Used by the semantic matcher
#                      AND by the keyword fallback (whole-word phrase match).
#   FALLBACK_RULES     verb / noun cues for the keyword fallback, so that
#                      "delete notes" or "open the calculator" still work.
#                      Keep bare verbs OUT of SUPPORTED_INTENTS: one-word
#                      examples give noisy embeddings in the semantic matcher.
#   ALLOWED_APPS / ALLOWED_RESOURCES   whitelists, matched as whole words.

# ---------------------------------------------------------------------------
# The nine core intents with English and Arabic training examples
# ---------------------------------------------------------------------------
SUPPORTED_INTENTS = {
    "LIST_FILES": {
        "en": ["show my files", "list files", "display directory",
               "show directory contents", "what files do i have"],
        "ar": ["اعرض ملفاتي", "عرض الملفات", "اعرض الملفات",
               "اطبع الملفات", "ما هي الملفات الموجودة"]
    },
    "CREATE_FILE": {
        "en": ["create a file", "create file", "make a new file",
               "add a file", "new file"],
        "ar": ["انشئ ملف", "انشئ ملف جديد", "عمل ملف جديد", "إضافة ملف"]
    },
    "CREATE_FOLDER": {
        "en": ["create a folder", "create folder", "make a new directory",
               "make a folder", "new folder"],
        "ar": ["انشئ مجلد", "انشئ مجلد جديد", "اصنع مجلد جديد", "انشاء فولدير"]
    },
    "RENAME_FILE": {
        "en": ["rename file", "rename a file", "change file name",
               "rename notes to report"],
        "ar": ["غير اسم الملف", "اعادة تسمية الملف", "غير اسم"]
    },
    "DELETE_FILE": {
        "en": ["delete file", "delete the file", "remove file",
               "remove the file"],
        "ar": ["احذف الملف", "امسح الملف"]
    },
    "OPEN_APPLICATION": {
        "en": ["open firefox", "launch browser", "open terminal",
               "open calculator", "open the calculator", "open text editor"],
        "ar": ["افتح فايرفوكس", "شغل المتصفح", "افتح التيرمينال",
               "افتح الحاسبة", "افتح محرر النصوص"]
    },
    "CLOSE_APPLICATION": {
        "en": ["close firefox", "quit browser", "close terminal",
               "close the browser", "close calculator"],
        "ar": ["اغلق فايرفوكس", "اقفل المتصفح", "اغلق التيرمينال",
               "اغلق الحاسبة"]
    },
    "SHOW_PROCESSES": {
        "en": ["show running processes", "list processes", "running programs"],
        "ar": ["اعرض العمليات", "العمليات الجارية", "عرض البرامج الشغالة"]
    },
    "SHOW_SYSTEM_USAGE": {
        "en": ["how much memory is used", "cpu usage", "disk space",
               "system usage", "show cpu usage", "memory usage"],
        "ar": ["كم الذاكرة المستخدمة", "استخدام المعالج", "مساحة القرص",
               "استهلاك الجهاز"]
    }
}

# Intents that must be confirmed by the user before they run
CONFIRMATION_INTENTS = {"DELETE_FILE", "CLOSE_APPLICATION"}

# ---------------------------------------------------------------------------
# Allowed applications (EN + AR) and their Ubuntu commands
# ---------------------------------------------------------------------------
ALLOWED_APPS = {
    "firefox": "firefox",
    "browser": "firefox",
    "web browser": "firefox",
    "فايرفوكس": "firefox",
    "المتصفح": "firefox",
    "متصفح": "firefox",
    "terminal": "gnome-terminal",
    "التيرمينال": "gnome-terminal",
    "تيرمينال": "gnome-terminal",
    "calculator": "gnome-calculator",
    "الحاسبة": "gnome-calculator",
    "حاسبة": "gnome-calculator",
    "files": "nautilus",
    "file manager": "nautilus",
    "مدير الملفات": "nautilus",
    "text editor": "gedit",
    "editor": "gedit",
    "محرر النصوص": "gedit"
}

# Allowed system resources (for the CPU / memory / disk usage command)
ALLOWED_RESOURCES = {
    "memory": "ram",
    "ram": "ram",
    "الذاكرة": "ram",
    "الرام": "ram",
    "cpu": "cpu",
    "processor": "cpu",
    "المعالج": "cpu",
    "disk": "disk",
    "storage": "disk",
    "space": "disk",
    "القرص": "disk",
    "المساحة": "disk"
}

# ---------------------------------------------------------------------------
# Keyword-fallback rules
#   verbs / nouns : cues (single words or short phrases, EN + AR).
#                   Everything is normalized and matched as WHOLE WORDS.
#   need_verb / need_noun : which side must be present for the rule to fire.
#   A cue present on the optional side only raises the confidence.
# ---------------------------------------------------------------------------
_APP_NAMES = list(ALLOWED_APPS)

FALLBACK_RULES = {
    "LIST_FILES": {
        "verbs": ["show", "list", "display", "print", "what are",
                  "what files", "which files",
                  "اعرض", "عرض", "اطبع", "ما هي", "ماهي"],
        "nouns": ["files", "directory", "directories", "folder", "folders",
                  "ملفاتي", "الملفات", "ملفات", "المجلد", "المجلدات"],
        "need_verb": True, "need_noun": True,
    },
    "CREATE_FILE": {
        "verbs": ["create", "make", "add", "new", "touch",
                  "انشئ", "انشاء", "عمل", "اضافة", "اصنع", "سوي"],
        "nouns": ["file", "ملف"],
        "need_verb": True, "need_noun": True,
    },
    "CREATE_FOLDER": {
        "verbs": ["create", "make", "add", "new",
                  "انشئ", "انشاء", "عمل", "اضافة", "اصنع", "سوي"],
        "nouns": ["folder", "directory", "dir", "مجلد", "فولدير", "فولدر"],
        "need_verb": True, "need_noun": True,
    },
    "RENAME_FILE": {
        "verbs": ["rename", "change name", "change file name",
                  "change the name",
                  "غير اسم", "اعادة تسمية", "تغيير اسم"],
        "nouns": ["file", "ملف"],
        "need_verb": True, "need_noun": False,
    },
    "DELETE_FILE": {
        "verbs": ["delete", "remove", "erase", "rm",
                  "احذف", "امسح", "ازل"],
        "nouns": ["file", "ملف"],
        "need_verb": True, "need_noun": False,
    },
    "OPEN_APPLICATION": {
        "verbs": ["open", "launch", "start", "run", "افتح", "شغل"],
        "nouns": _APP_NAMES,
        "need_verb": True, "need_noun": False,
    },
    "CLOSE_APPLICATION": {
        "verbs": ["close", "quit", "exit", "kill", "اغلق", "اقفل", "سكر"],
        "nouns": _APP_NAMES,
        "need_verb": True, "need_noun": False,
    },
    "SHOW_PROCESSES": {
        "verbs": ["show", "list", "display", "اعرض", "عرض"],
        "nouns": ["processes", "process", "running programs",
                  "running processes", "running apps",
                  "العمليات", "عمليات", "العمليات الجارية",
                  "البرامج الشغالة", "البرامج الجارية"],
        "need_verb": False, "need_noun": True,
    },
    "SHOW_SYSTEM_USAGE": {
        "verbs": ["show", "check", "display", "how much", "اعرض", "كم"],
        "nouns": ["memory", "ram", "cpu", "disk", "storage", "space",
                  "usage", "processor",
                  "الذاكرة", "الرام", "المعالج", "القرص", "المساحة",
                  "استهلاك", "استخدام"],
        "need_verb": False, "need_noun": True,
    },
}

# ---------------------------------------------------------------------------
# Linguistic data used by parameter extraction and the multi-command guard
# ---------------------------------------------------------------------------

# Words that introduce a file / folder name: "create a file CALLED notes"
NAME_MARKERS = ["called", "named", "اسمه", "اسمها", "باسم", "المسمى"]

# Words that separate old and new name: "rename notes TO report"
RENAME_SEPARATORS = ["to", "as", "into", "الى", "إلى"]

# Ignored when measuring how much of the sentence a match explains
STOPWORDS = [
    "a", "an", "the", "my", "me", "please", "pls", "plz", "kindly", "now",
    "can", "you", "could", "would", "will", "i", "it", "this", "that",
    "to", "of", "for", "is", "are", "called", "named", "thanks", "thank",
    "لو", "سمحت", "من", "فضلك", "الان", "ارجوك", "لي",
]

# Skipped when looking for a file name (on top of the command words)
NAME_FILLER = STOPWORDS + [
    "with", "new", "name", "file", "files", "folder", "folders", "directory",
    "dir", "want", "need", "like", "again", "quickly", "fast", "immediately",
    "بسرعة",
    "ملف", "الملف", "مجلد", "المجلد", "جديد", "جديدة", "اسم", "اسمه",
    "اسمها", "باسم", "المسمى",
]

# A name that means "everything" is never accepted as a single file name
BLOCKED_NAMES = ["everything", "all", "كل", "الكل", "كله", "كلشي"]

# Multi-command guard
CONJUNCTION_WORDS = ["and", "then", "و", "ثم", "وبعدين", "بعدين"]
CONJUNCTION_PHRASES = [("after", "that"), ("بعد", "ذلك")]
CONJUNCTION_CHARS = ";&"