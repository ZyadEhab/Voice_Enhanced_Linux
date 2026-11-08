from __future__ import annotations
 
from dataclasses import dataclass, field
from pathlib import Path
 
# The ONLY folder file operations may touch. Tests replace this value.
WORKSPACE: Path = Path.home() / "VoiceLinuxWorkspace"
 
MAX_NAME_LENGTH = 100
MAX_SPOKEN_ITEMS = 10  # do not read out hundreds of names
 
 
@dataclass
class OperationResult:
    """Result of one operation (shared shape from Section 9.2)."""
 
    success: bool
    message: str
    items: list = field(default_factory=list)
 
 
MESSAGES = {
    "en": {
        "name_empty": "The name is empty. Please say a name.",
        "name_slash": "The name cannot contain slashes.",
        "name_dots": "That name is not allowed.",
        "name_hidden": "Names cannot start with a dot.",
        "name_long": "The name is too long.",
        "outside": "That location is outside the safe folder.",
        "file_created": "File {name} was created.",
        "folder_created": "Folder {name} was created.",
        "exists": "{name} already exists.",
        "list_empty": "Your workspace is empty.",
        "list_result": "You have {count} items: {names}.",
        "failed": "The operation failed.",
    },
    "ar": {
        "name_empty": "الاسم فارغ. من فضلك قل اسما.",
        "name_slash": "لا يمكن أن يحتوي الاسم على شرطة مائلة.",
        "name_dots": "هذا الاسم غير مسموح.",
        "name_hidden": "لا يمكن أن يبدأ الاسم بنقطة.",
        "name_long": "الاسم طويل جدا.",
        "outside": "هذا المكان خارج المجلد الآمن.",
        "file_created": "تم إنشاء الملف {name}.",
        "folder_created": "تم إنشاء المجلد {name}.",
        "exists": "{name} موجود بالفعل.",
        "list_empty": "مساحة العمل فارغة.",
        "list_result": "لديك {count} عناصر: {names}.",
        "failed": "فشلت العملية.",
    },
}
 
 
def _msg(language: str, key: str, **values) -> str:
    table = MESSAGES.get(language, MESSAGES["en"])
    return table[key].format(**values)
 
 
def _fail(language: str, key: str, **values) -> OperationResult:
    return OperationResult(False, _msg(language, key, **values), [])
 
 
# --------------------------------------------------------------------------
# Workspace
# --------------------------------------------------------------------------
def ensure_workspace() -> Path:
    """Create the workspace with owner-only permissions (mode 700)."""
    WORKSPACE.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        WORKSPACE.chmod(0o700)  # also fixes a folder created earlier
    except OSError:
        pass  # e.g. filesystems without Unix permissions
    return WORKSPACE
 
 
# --------------------------------------------------------------------------
# Validation helpers
# --------------------------------------------------------------------------
def validate_name(name) -> str | None:
    """Return None if the name is safe, otherwise a message key explaining why."""
    if not isinstance(name, str) or not name.strip():
        return "name_empty"
    name = name.strip()
    if "/" in name or "\\" in name or "\x00" in name:
        return "name_slash"
    if name in (".", ".."):
        return "name_dots"
    if name.startswith("."):
        return "name_hidden"  # hidden files would be invisible to list_files
    if len(name) > MAX_NAME_LENGTH:
        return "name_long"
    return None
 
 
def resolve_in_workspace(name: str) -> Path | None:
    """Join name to the workspace, resolve it, and make sure it stays inside.
 
    resolve() follows symlinks, so a link pointing outside is detected.
    Returns None if the final path is outside the workspace.
    """
    root = WORKSPACE.resolve()
    target = (root / name.strip()).resolve()
    if target == root or not target.is_relative_to(root):
        return None
    return target
 
 
def _checked_path(name, language: str):
    """Validate a name and resolve it. Returns (path, None) or (None, error)."""
    problem = validate_name(name)
    if problem:
        return None, _fail(language, problem)
    path = resolve_in_workspace(name)
    if path is None:
        return None, _fail(language, "outside")
    return path, None
 
 
# --------------------------------------------------------------------------
# Operations
# --------------------------------------------------------------------------
def list_files(language: str = "en") -> OperationResult:
    """List the workspace: folders first, hidden items skipped."""
    try:
        ensure_workspace()
        entries = [p for p in WORKSPACE.iterdir() if not p.name.startswith(".")]
        folders = sorted(p.name for p in entries if p.is_dir())
        files = sorted(p.name for p in entries if not p.is_dir())
    except OSError:
        return _fail(language, "failed")
 
    names = folders + files
    if not names:
        return OperationResult(True, _msg(language, "list_empty"), [])
 
    spoken = ", ".join(names[:MAX_SPOKEN_ITEMS])
    message = _msg(language, "list_result", count=len(names), names=spoken)
    return OperationResult(True, message, names)
 
 
def create_file(name, language: str = "en") -> OperationResult:
    """Create an empty file. Adds .txt if there is no extension. Never overwrites."""
    problem = validate_name(name)
    if problem:
        return _fail(language, problem)
    name = name.strip()
    if not Path(name).suffix:
        name += ".txt"
 
    try:
        ensure_workspace()
        path, error = _checked_path(name, language)
        if error:
            return error
        with open(path, "x"):  # mode "x" = fail if the file already exists
            pass
    except FileExistsError:
        return _fail(language, "exists", name=name)
    except OSError:
        return _fail(language, "failed")
    return OperationResult(True, _msg(language, "file_created", name=name), [name])
 
 
def create_folder(name, language: str = "en") -> OperationResult:
    """Create a folder. Fails if it already exists."""
    try:
        ensure_workspace()
        path, error = _checked_path(name, language)
        if error:
            return error
        path.mkdir()  # exist_ok=False -> FileExistsError if present
    except FileExistsError:
        return _fail(language, "exists", name=name.strip())
    except OSError:
        return _fail(language, "failed")
    return OperationResult(
        True, _msg(language, "folder_created", name=name.strip()), [name.strip()]
    )
 