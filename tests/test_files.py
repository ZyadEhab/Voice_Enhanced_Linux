import os
import stat
import sys
 
import pytest
 
from execution import files
 
 
@pytest.fixture(autouse=True)
def temp_workspace(tmp_path, monkeypatch):
    """Point the module at a throwaway workspace for every test."""
    workspace = tmp_path / "VoiceLinuxWorkspace"
    monkeypatch.setattr(files, "WORKSPACE", workspace)
    return workspace
 
 
# ---------------------------------------------------------------- workspace
def test_ensure_workspace_creates_folder(temp_workspace):
    files.ensure_workspace()
    assert temp_workspace.is_dir()
 
 
@pytest.mark.skipif(sys.platform == "win32", reason="Unix permissions only")
def test_workspace_is_mode_700(temp_workspace):
    files.ensure_workspace()
    assert stat.S_IMODE(os.stat(temp_workspace).st_mode) == 0o700
 
 
# ---------------------------------------------------------------- list_files
def test_list_empty_workspace():
    result = files.list_files()
    assert result.success and result.items == []
    assert "empty" in result.message
 
 
def test_list_folders_first_and_skips_hidden(temp_workspace):
    files.ensure_workspace()
    (temp_workspace / "b.txt").write_text("x")
    (temp_workspace / "a.txt").write_text("x")
    (temp_workspace / "Zfolder").mkdir()
    (temp_workspace / ".secret").write_text("x")
    result = files.list_files()
    assert result.items == ["Zfolder", "a.txt", "b.txt"]
    assert ".secret" not in result.message
 
 
def test_list_message_is_arabic_when_requested(temp_workspace):
    files.ensure_workspace()
    (temp_workspace / "a.txt").write_text("x")
    assert "لديك" in files.list_files("ar").message
 
 
def test_list_limits_spoken_names(temp_workspace):
    files.ensure_workspace()
    for i in range(25):
        (temp_workspace / f"f{i:02}.txt").write_text("x")
    result = files.list_files()
    assert len(result.items) == 25  # full list returned for the GUI
    assert "f24.txt" not in result.message  # but not all of it is read aloud
 
 
# --------------------------------------------------------------- create_file
def test_create_file_adds_txt_extension(temp_workspace):
    result = files.create_file("notes")
    assert result.success
    assert (temp_workspace / "notes.txt").is_file()
    assert result.items == ["notes.txt"]
 
 
def test_create_file_keeps_existing_extension(temp_workspace):
    assert files.create_file("data.csv").success
    assert (temp_workspace / "data.csv").is_file()
 
 
def test_create_file_never_overwrites(temp_workspace):
    files.ensure_workspace()
    (temp_workspace / "notes.txt").write_text("important")
    result = files.create_file("notes")
    assert not result.success
    assert "already exists" in result.message
    assert (temp_workspace / "notes.txt").read_text() == "important"
 
 
def test_create_file_arabic_name(temp_workspace):
    result = files.create_file("ملاحظات", "ar")
    assert result.success
    assert (temp_workspace / "ملاحظات.txt").is_file()
    assert "تم إنشاء الملف" in result.message
 
 
def test_create_file_arabic_already_exists_message(temp_workspace):
    files.create_file("ملاحظات", "ar")
    result = files.create_file("ملاحظات", "ar")
    assert not result.success
    assert "موجود بالفعل" in result.message
 
 
# ------------------------------------------------------------- create_folder
def test_create_folder(temp_workspace):
    result = files.create_folder("Project")
    assert result.success
    assert (temp_workspace / "Project").is_dir()
 
 
def test_create_folder_fails_if_exists(temp_workspace):
    files.create_folder("Project")
    result = files.create_folder("Project")
    assert not result.success
    assert "already exists" in result.message
 
 
def test_create_folder_arabic_name(temp_workspace):
    assert files.create_folder("مشروع", "ar").success
    assert (temp_workspace / "مشروع").is_dir()
 
 
# ---------------------------------------------- security: bad names rejected
@pytest.mark.parametrize(
    "bad_name",
    ["", "   ", ".", "..", "../evil", "a/b", "a\\b", "/etc/passwd",
     ".hidden", "x" * 101, "bad\x00name", None, 123],
)
def test_bad_names_rejected_everywhere(bad_name, temp_workspace):
    assert not files.create_file(bad_name).success
    assert not files.create_folder(bad_name).success
 
 
def test_name_of_exactly_100_chars_is_allowed():
    assert files.validate_name("x" * 100) is None
 
 
def test_path_traversal_creates_nothing_outside(temp_workspace):
    result = files.create_file("../escaped")
    assert not result.success
    assert not (temp_workspace.parent / "escaped.txt").exists()
    assert not (temp_workspace.parent / "escaped").exists()
 
 
def test_injection_style_name_is_just_a_name_never_executed(temp_workspace):
    """A spoken '; rm -rf ~' must become a harmless file name, not a command."""
    result = files.create_file("notes; rm -rf ~")
    assert result.success
    assert (temp_workspace / "notes; rm -rf ~.txt").is_file()
 
 
def test_injection_with_slash_is_rejected():
    assert not files.create_folder("x; rm -rf /").success
 
 
def test_symlink_escape_is_blocked(temp_workspace, tmp_path):
    files.ensure_workspace()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = temp_workspace / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not available on this system")
    # "link" resolves outside the workspace, so it must be refused
    result = files.create_folder("link")
    assert not result.success
    assert files.resolve_in_workspace("link") is None
 
 
def test_error_messages_are_arabic_when_requested():
    assert "فارغ" in files.create_file("", "ar").message
    assert "خارج" in files.create_file("../x", "ar").message or \
           "شرطة" in files.create_file("../x", "ar").message
 