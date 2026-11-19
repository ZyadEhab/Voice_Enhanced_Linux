# nlp/intents.py
#
# Data only: no logic lives here. nlp/nlp.py reads everything below.

SUPPORTED_INTENTS = {
    "LIST_FILES": {
        "en": ["show my files", "list files", "display directory",
               "show directory contents", "what files do i have"],
        "ar": ["اعرض ملفاتي", "عرض الملفات", "اعرض الملفات",
               "اطبع الملفات", "ما هي الملفات الموجودة",
               "وريني ملفاتي", "شوفلي الملفات"]
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
               "rename notes to report", "rename notes to report file"],
        "ar": ["غير اسم الملف", "اعادة تسمية الملف", "غير اسم",
               "غير اسم notes الى report", "غير اسم الملف من notes الى report"]
    },
    "DELETE_FILE": {
        "en": ["delete file", "delete the file", "remove file",
               "remove the file"],
        "ar": ["احذف الملف", "امسح الملف"]
    },
    "OPEN_APPLICATION": {
        "en": ["open firefox", "launch browser", "open terminal",
               "open calculator", "open the calculator", "open text editor",
               "open gedit", "open nautilus", "open files"],
        "ar": ["افتح فايرفوكس", "شغل المتصفح", "افتح التيرمينال",
               "افتح الحاسبة", "افتح محرر النصوص", "افتح المتصفح",
               "شغل الحاسبة", "افتح مدير الملفات"]
    },
    "CLOSE_APPLICATION": {
        "en": ["close firefox", "quit browser", "close terminal",
               "close the browser", "close calculator"],
        "ar": ["اغلق فايرفوكس", "اقفل المتصفح", "اغلق التيرمينال",
               "اغلق الحاسبة", "اقفل التيرمينال"]
    },
    "SHOW_PROCESSES": {
        "en": ["show running processes", "list processes", "running programs",
               "what is running on my computer", "show tasks", "what's running right now"],
        "ar": ["اعرض العمليات", "العمليات الجارية", "عرض البرامج الشغالة",
               "اعرض البرامج المفتوحة"]
    },
    "SHOW_SYSTEM_USAGE": {
        "en": ["how much memory is used", "cpu usage", "disk space",
               "system usage", "show cpu usage", "memory usage", 
               "how is my ram doing", "how much disk space is left", 
               "how much storage do i have"],
        "ar": ["كم الذاكرة المستخدمة", "استخدام المعالج", "مساحة القرص",
               "استهلاك الجهاز", "اعرض الرام", "ايه استخدام المعالج",
               "كم المساحة المتبقية على القرص"]
    }
}

# Intents that must be confirmed by the user before they run
CONFIRMATION_INTENTS = {"DELETE_FILE", "CLOSE_APPLICATION"}

# Allowed applications (EN + AR) and their Ubuntu commands
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
    "gedit": "gedit",
    "nautilus": "nautilus",
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

_APP_NAMES = list(ALLOWED_APPS)

FALLBACK_RULES = {
    "LIST_FILES": {
        "verbs": ["show", "list", "display", "print", "what are",
                  "what files", "which files", "give me", "get me",
                  "اعرض", "عرض", "اطبع", "ما هي", "ماهي",
                  "شوفلي", "شوف", "وريني", "ورني", "هات", "هاتلي"],
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
                  "tasks", "task manager", "whats running", "what is running",
                  "العمليات", "عمليات", "العمليات الجارية",
                  "البرامج الشغالة", "البرامج الجارية",
                  "البرامج المفتوحة", "التطبيقات المفتوحة",
                  "التطبيقات الشغالة"],
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

NAME_MARKERS = ["called", "named", "اسمه", "اسمها", "باسم", "المسمى"]
RENAME_SEPARATORS = ["to", "as", "into", "الى", "إلى"]
STOPWORDS = [
    "a", "an", "the", "my", "me", "please", "pls", "plz", "kindly", "now",
    "can", "you", "could", "would", "will", "i", "it", "this", "that",
    "to", "of", "for", "is", "are", "called", "named", "thanks", "thank",
    "لو", "سمحت", "من", "فضلك", "الان", "ارجوك", "لي",
]
NAME_FILLER = STOPWORDS + [
    "with", "new", "name", "file", "files", "folder", "folders", "directory",
    "dir", "want", "need", "like", "again", "quickly", "fast", "immediately",
    "بسرعة", "all", "every", "كل", "جميع", "الملفات", "ملفات",
    "ملف", "الملف", "مجلد", "المجلد", "جديد", "جديدة", "اسم", "اسمه",
    "اسمها", "باسم", "المسمى",
]
BLOCKED_NAMES = ["everything", "all", "كل", "الكل", "كله", "كلشي",
                 "شيء", "شي", "شيئ", "الملفات", "ملفات", "files"]
MASS_WORDS = ["everything", "all", "every", "whole", "كل", "الكل", "كله",
              "كلها", "جميع", "كلشي", "شيء", "شي", "شيئ"]
CONJUNCTION_WORDS = ["and", "then", "و", "ثم", "وبعدين", "بعدين"]
CONJUNCTION_PHRASES = [("after", "that"), ("بعد", "ذلك")]
CONJUNCTION_CHARS = ";&"
# Words that must NEVER be passed to the semantic matcher
BLOCKED_PHRASES = ["shutdown", "reboot", "restart", "اطفئ الجهاز", "اقفل الجهاز"]