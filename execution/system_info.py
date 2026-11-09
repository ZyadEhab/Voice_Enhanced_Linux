"""System information via psutil. Every function returns a speakable sentence (en / ar)."""
import psutil

MSG = {
    "en": {
        "cpu": "The CPU usage is currently at {p} percent.",
        "ram": "You are using {p} percent of your RAM, {u} of {t} gigabytes.",
        "disk": "Your main disk is {p} percent full, with {f} gigabytes free.",
        "unknown": "I do not know how to check that resource.",
        "error": "I encountered an error checking the {r} usage.",
        "procs": "There are currently {n} processes running. The biggest memory users are {names}.",
        "procs_err": "I could not retrieve the running processes.",
    },
    "ar": {
        "cpu": "استخدام المعالج حاليا {p} بالمئة.",
        "ram": "تستخدم {p} بالمئة من الذاكرة، {u} من {t} جيجابايت.",
        "disk": "القرص الرئيسي ممتلئ بنسبة {p} بالمئة، والمتاح {f} جيجابايت.",
        "unknown": "لا أعرف كيف أفحص هذا المورد.",
        "error": "حدث خطأ أثناء فحص الاستخدام.",
        "procs": "يوجد حاليا {n} عملية تعمل. أكثر البرامج استخداما للذاكرة: {names}.",
        "procs_err": "تعذر الحصول على العمليات الجارية.",
    },
}


def _m(language: str, key: str, **v) -> str:
    return MSG.get(language, MSG["en"])[key].format(**v)


def get_system_usage(resource: str, language: str = "en") -> str:
    try:
        if resource == "cpu":
            return _m(language, "cpu", p=psutil.cpu_percent(interval=0.5))
        if resource == "ram":
            r = psutil.virtual_memory()
            return _m(language, "ram", p=r.percent, u=f"{r.used / 2**30:.1f}", t=f"{r.total / 2**30:.1f}")
        if resource == "disk":
            d = psutil.disk_usage("/")
            return _m(language, "disk", p=d.percent, f=f"{d.free / 2**30:.0f}")
        return _m(language, "unknown")
    except Exception:
        return _m(language, "error", r=resource)


def get_running_processes(top: int = 3, language: str = "en") -> str:
    """Count plus the heaviest few by memory: useful on screen, still short to speak."""
    try:
        procs = [(p.info.get("memory_percent") or 0.0, p.info.get("name") or "unknown")
                 for p in psutil.process_iter(["name", "memory_percent"])]
        procs.sort(reverse=True)
        names = []
        for _, n in procs:
            if n not in names:
                names.append(n)
            if len(names) == top:
                break
        return _m(language, "procs", n=len(procs), names=", ".join(names))
    except Exception:
        return _m(language, "procs_err")
