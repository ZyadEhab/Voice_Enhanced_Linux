# nlp/intents.py

# النوايا التسع الأساسية مع أمثلة التدريب بالإنجليزية والعربية
SUPPORTED_INTENTS = {
    "LIST_FILES": {
        "en": ["show my files", "list files", "display directory", "show directory contents"],
        "ar": ["اعرض ملفاتي", "عرض الملفات", "اطبع الملفات", "ما هي الملفات الموجودة"]
    },
    "CREATE_FILE": {
        "en": ["create a file", "make a new file", "add a file"],
        "ar": ["انشئ ملف", "عمل ملف جديد", "إضافة ملف"]
    },
    "CREATE_FOLDER": {
        "en": ["create a folder", "make a new directory", "new folder"],
        "ar": ["انشئ مجلد", "اصنع مجلد جديد", "انشاء فولدير"]
    },
    "RENAME_FILE": {
        "en": ["rename file", "change file name", "rename notes to report"],
        "ar": ["غير اسم الملف", "اعادة تسمية الملف", "غير اسم"]
    },
    "DELETE_FILE": {
        "en": ["delete file", "remove file", "delete report"],
        "ar": ["احذف الملف", "امسح الملف", "احذف"]
    },
    "OPEN_APPLICATION": {
        "en": ["open firefox", "launch browser", "open terminal", "open calculator"],
        "ar": ["افتح فايرفوكس", "شغل المتصفح", "افتح التيرمينال", "افتح الحاسبة"]
    },
    "CLOSE_APPLICATION": {
        "en": ["close firefox", "quit browser", "close terminal"],
        "ar": ["اغلق فايرفوكس", "اقفل المتصفح", "اغلق التيرمينال"]
    },
    "SHOW_PROCESSES": {
        "en": ["show running processes", "list processes", "running programs"],
        "ar": ["اعرض العمليات", "العمليات الجارية", "عرض البرامج الشغالة"]
    },
    "SHOW_SYSTEM_USAGE": {
        "en": ["how much memory is used", "cpu usage", "disk space", "system usage"],
        "ar": ["كم الذاكرة المستخدمة", "استخدام المعالج", "مساحة القرص", "استهلاك الجهاز"]
    }
}

# أسماء التطبيقات المسموحة باللغتين وما يقابلها في أوبونتو
ALLOWED_APPS = {
    "firefox": "firefox",
    "browser": "firefox",
    "فايرفوكس": "firefox",
    "المتصفح": "firefox",
    "terminal": "gnome-terminal",
    "التيرمينال": "gnome-terminal",
    "calculator": "gnome-calculator",
    "الحاسبة": "gnome-calculator",
    "files": "nautilus",
    "text editor": "gedit",
    "محرر النصوص": "gedit"
}

# موارد النظام المسموحة (لأمر استهلاك المعالج/الذاكرة/القرص)
ALLOWED_RESOURCES = {
    "memory": "ram",
    "ram": "ram",
    "الذاكرة": "ram",
    "cpu": "cpu",
    "المعالج": "cpu",
    "disk": "disk",
    "storage": "disk",
    "space": "disk",
    "القرص": "disk",
    "المساحة": "disk"
}