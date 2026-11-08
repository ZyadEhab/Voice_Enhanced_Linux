"""System information via psutil. Every function returns a speakable sentence."""
import psutil


def get_system_usage(resource: str) -> str:
    try:
        if resource == "cpu":
            return f"The CPU usage is currently at {psutil.cpu_percent(interval=0.5)} percent."
        if resource == "ram":
            ram = psutil.virtual_memory()
            used, total = ram.used / 2**30, ram.total / 2**30
            return (f"You are using {ram.percent} percent of your RAM, "
                    f"{used:.1f} of {total:.1f} gigabytes.")
        if resource == "disk":
            disk = psutil.disk_usage("/")
            free = disk.free / 2**30
            return f"Your main disk is {disk.percent} percent full, with {free:.0f} gigabytes free."
        return "I do not know how to check that resource."
    except Exception:
        return f"I encountered an error checking the {resource} usage."


def get_running_processes(top: int = 3) -> str:
    """Count plus the heaviest few by memory, so the result is useful but still short to speak."""
    try:
        procs = []
        for p in psutil.process_iter(["name", "memory_percent"]):
            procs.append((p.info.get("memory_percent") or 0.0, p.info.get("name") or "unknown"))
        procs.sort(reverse=True)
        names = []
        for _, n in procs:
            if n not in names:
                names.append(n)
            if len(names) == top:
                break
        return (f"There are currently {len(procs)} processes running. "
                f"The biggest memory users are {', '.join(names)}.")
    except Exception:
        return "I could not retrieve the running processes."


if __name__ == "__main__":
    for r in ("ram", "cpu", "disk"):
        print(get_system_usage(r))
    print(get_running_processes())
