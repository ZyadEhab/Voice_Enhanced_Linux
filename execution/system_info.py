import psutil

def get_system_usage(resource: str) -> str:
    """Returns a speakable string about CPU, RAM, or Disk usage."""
    try:
        if resource == "cpu":
            usage = psutil.cpu_percent(interval=0.5)
            return f"The CPU usage is currently at {usage} percent."
        elif resource == "ram":
            ram = psutil.virtual_memory()
            return f"You are using {ram.percent} percent of your system RAM."
        elif resource == "disk":
            disk = psutil.disk_usage('/')
            return f"Your main disk is {disk.percent} percent full."
        
        return "I do not know how to check that resource."
    except Exception as e:
        # Prevent crashes; return a speakable error message instead
        return f"I encountered an error checking the {resource} usage."

def get_running_processes() -> str:
    """Returns a speakable string about the number of running processes."""
    try:
        # A count is much better for TTS than reading hundreds of process names
        count = len(psutil.pids())
        return f"There are currently {count} processes running on the system."
    except Exception as e:
        return "I could not retrieve the running processes."

# Quick local test to verify it works
if __name__ == "__main__":
    print("Testing RAM:", get_system_usage("ram"))
    print("Testing CPU:", get_system_usage("cpu"))
    print("Testing Processes:", get_running_processes())