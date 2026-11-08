import subprocess
from dataclasses import dataclass
from execution.system_info import get_system_usage, get_running_processes

# NOTE: You will import Karim Amr's modules here once he pushes his code
# from execution.files import handle_file_intent

@dataclass
class ExecutionResult:
    success: bool
    message: str

def execute(intent_data: dict) -> ExecutionResult:
    intent_name = intent_data.get("intent")
    params = intent_data.get("params", {})
    
    try:
        # Route 1: System Information
        if intent_name == "SHOW_SYSTEM_USAGE":
            msg = get_system_usage(params.get("resource"))
            return ExecutionResult(True, msg)
            
        elif intent_name == "SHOW_PROCESSES":
            msg = get_running_processes()
            return ExecutionResult(True, msg)
            
        # Route 2: Applications
        elif intent_name == "OPEN_APPLICATION":
            app = params.get("app")
            # CRITICAL SECURITY: Passed as a list. shell=True is strictly avoided.
            subprocess.Popen([app])
            return ExecutionResult(True, f"The application {app} has been opened.")
            
        elif intent_name == "CLOSE_APPLICATION":
            app = params.get("app")
            subprocess.run(["killall", app], check=False)
            return ExecutionResult(True, f"The application {app} has been closed.")
            
        # Route 3: File Management (Placeholder until Karim's code is merged)
        elif intent_name in {"LIST_FILES", "CREATE_FILE", "CREATE_FOLDER", "RENAME_FILE", "DELETE_FILE"}:
            return ExecutionResult(False, "File operations are waiting for the file management module.")
            
        else:
            return ExecutionResult(False, "I do not know how to execute that command.")
            
    except Exception as e:
        # Failures must become speakable messages, not system crashes
        return ExecutionResult(False, f"The operation failed. {str(e)}")

# Quick local test to verify the routing works
if __name__ == "__main__":
    test_intent = {"intent": "SHOW_SYSTEM_USAGE", "params": {"resource": "cpu"}}
    print(f"Test Result: {execute(test_intent)}")