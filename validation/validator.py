from dataclasses import dataclass
from pathlib import Path

@dataclass
class ValidationResult:
    allowed: bool
    needs_confirmation: bool
    reason: str

# Fixed allow-lists based on project specs
ALLOWED_INTENTS = {
    "LIST_FILES", "CREATE_FILE", "CREATE_FOLDER", "RENAME_FILE", 
    "DELETE_FILE", "OPEN_APPLICATION", "CLOSE_APPLICATION", 
    "SHOW_PROCESSES", "SHOW_SYSTEM_USAGE"
}

ALLOWED_APPS = {"firefox", "gnome-terminal", "gnome-calculator", "nautilus", "gedit"}
ALLOWED_RESOURCES = {"ram", "cpu", "disk"}

WORKSPACE = Path.home() / "VoiceLinuxWorkspace"

def validate(intent_data: dict) -> ValidationResult:
    intent_name = intent_data.get("intent")
    params = intent_data.get("params", {})
    
    # 1. Reject unknown intents
    if intent_name not in ALLOWED_INTENTS:
        return ValidationResult(False, False, "Intent not allowed or recognized.")
        
    # 2. Flag dangerous actions that need user confirmation
    needs_conf = intent_name in {"DELETE_FILE", "CLOSE_APPLICATION"}
    
    # 3. Validate application names
    if intent_name in {"OPEN_APPLICATION", "CLOSE_APPLICATION"}:
        app_name = params.get("app")
        if app_name not in ALLOWED_APPS:
            return ValidationResult(False, False, "Application is not on the safe list.")
            
    # 4. Validate system resources
    if intent_name == "SHOW_SYSTEM_USAGE":
        resource = params.get("resource")
        if resource not in ALLOWED_RESOURCES:
            return ValidationResult(False, False, "System resource not recognized.")
            
    # 5. Security: Validate file/folder names to prevent path traversal
    if "file" in params or "folder" in params:
        target_name = params.get("file") or params.get("folder")
        if target_name:
            # Block slashes and dot-navigation to keep operations inside ~/VoiceLinuxWorkspace
            if "/" in target_name or "\\" in target_name or target_name in {".", ".."}:
                return ValidationResult(False, False, "Invalid characters in file name. Path traversal blocked.")
                
    return ValidationResult(True, needs_conf, "Allowed")

# Quick local test to verify it works (this won't run when imported by main.py)
if __name__ == "__main__":
    test_intent = {"intent": "DELETE_FILE", "params": {"file": "report.txt"}}
    print(f"Test Result: {validate(test_intent)}") 
    # Should print: ValidationResult(allowed=True, needs_confirmation=True, reason='Allowed')