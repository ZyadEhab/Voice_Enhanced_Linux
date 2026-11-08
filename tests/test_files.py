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
 
 
# ------------------------------------------------------------- rename_file
def test_rename_file_keeps_txt_extension(temp_workspace):
    files.create_file("notes")
    result = files.rename_file("notes", "report")
    assert result.success
    assert (temp_workspace / "report.txt").is_file()
    assert not (temp_workspace / "notes.txt").exists()
    assert result.items == ["report.txt"]
 
 
def test_rename_file_with_explicit_extension(temp_workspace):
    files.create_file("data.csv")
    assert files.rename_file("data.csv", "table.csv").success
    assert (temp_workspace / "table.csv").is_file()
 
 
def test_rename_folder_adds_no_extension(temp_workspace):
    files.create_folder("Project")
    assert files.rename_file("Project", "Work").success
    assert (temp_workspace / "Work").is_dir()
 
 
def test_rename_missing_item():
    result = files.rename_file("ghost", "x")
    assert not result.success
    assert "could not find" in result.message
 
 
def test_rename_never_overwrites(temp_workspace):
    files.create_file("a")
    files.create_file("b")
    (temp_workspace / "b.txt").write_text("keep me")
    result = files.rename_file("a", "b")
    assert not result.success
    assert "already exists" in result.message
    assert (temp_workspace / "b.txt").read_text() == "keep me"
    assert (temp_workspace / "a.txt").exists()
 
 
def test_rename_arabic(temp_workspace):
    files.create_file("ملاحظات", "ar")
    result = files.rename_file("ملاحظات", "تقرير", "ar")
    assert result.success
    assert (temp_workspace / "تقرير.txt").is_file()
    assert "تمت إعادة تسمية" in result.message
 
 
@pytest.mark.parametrize("bad_new", ["", "../evil", "a/b", "..", ".hidden"])
def test_rename_rejects_bad_new_names(bad_new, temp_workspace):
    files.create_file("notes")
    assert not files.rename_file("notes", bad_new).success
    assert (temp_workspace / "notes.txt").exists()
    assert not (temp_workspace.parent / "evil").exists()
 
 
@pytest.mark.parametrize("bad_old", ["", "../x", "/etc/passwd", "a/b", "..", None])
def test_rename_rejects_bad_old_names(bad_old):
    assert not files.rename_file(bad_old, "new").success
 
 
# ------------------------------------------------------------- delete_file
def test_delete_file_by_short_name(temp_workspace):
    files.create_file("report")
    result = files.delete_file("report")
    assert result.success
    assert not (temp_workspace / "report.txt").exists()
    assert "deleted" in result.message
 
 
def test_delete_prefers_exact_name(temp_workspace):
    files.ensure_workspace()
    (temp_workspace / "report").write_text("exact")
    (temp_workspace / "report.txt").write_text("other")
    assert files.delete_file("report").success
    assert not (temp_workspace / "report").exists()
    assert (temp_workspace / "report.txt").exists()
 
 
def test_delete_empty_folder(temp_workspace):
    files.create_folder("Old")
    assert files.delete_file("Old").success
    assert not (temp_workspace / "Old").exists()
 
 
def test_delete_never_removes_folder_contents(temp_workspace):
    files.create_folder("Project")
    (temp_workspace / "Project" / "inside.txt").write_text("x")
    result = files.delete_file("Project")
    assert not result.success
    assert "not empty" in result.message
    assert (temp_workspace / "Project" / "inside.txt").exists()
 
 
def test_delete_missing_item():
    result = files.delete_file("ghost")
    assert not result.success
    assert "could not find" in result.message
 
 
def test_delete_arabic(temp_workspace):
    files.create_file("ملاحظات", "ar")
    result = files.delete_file("ملاحظات", "ar")
    assert result.success
    assert "تم حذف" in result.message
    assert not (temp_workspace / "ملاحظات.txt").exists()
 
 
@pytest.mark.parametrize(
    "bad_name", ["", "..", "../outside", "/etc/passwd", "a/b", ".", None]
)
def test_delete_rejects_bad_names(bad_name):
    assert not files.delete_file(bad_name).success
 
 
def test_delete_cannot_touch_files_outside_workspace(temp_workspace):
    files.ensure_workspace()
    outside = temp_workspace.parent / "outside.txt"
    outside.write_text("precious")
    assert not files.delete_file("../outside.txt").success
    assert outside.read_text() == "precious"
 
 
def test_delete_symlink_pointing_outside_is_refused(temp_workspace, tmp_path):
    files.ensure_workspace()
    target = tmp_path / "secret.txt"
    target.write_text("precious")
    link = temp_workspace / "link.txt"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not available on this system")
    assert not files.delete_file("link").success
    assert target.read_text() == "precious"
 