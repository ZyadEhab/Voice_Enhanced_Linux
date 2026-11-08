import pytest
 
from execution import apps
 
 
class FakeProcess:
    def __init__(self, pid, name):
        self.pid = pid
        self.info = {"pid": pid, "name": name}
        self.terminated = False
        self.killed = False
 
    def terminate(self):
        self.terminated = True
 
    def kill(self):
        self.killed = True
 
 
class FakePsutil:
    class Error(Exception):
        pass
 
    class NoSuchProcess(Error):
        pass
 
    class AccessDenied(Error):
        pass
 
    def __init__(self, procs=(), stubborn=()):
        self.procs = list(procs)
        self.stubborn = set(stubborn)
 
    def process_iter(self, attrs=None):
        return list(self.procs)
 
    def wait_procs(self, procs, timeout=None):
        gone = [p for p in procs if p.pid not in self.stubborn]
        alive = [p for p in procs if p.pid in self.stubborn]
        return gone, alive
 
 
class Launcher:
    """Records every Popen call instead of starting anything."""
 
    def __init__(self):
        self.calls = []
        self.fail = False
 
    def __call__(self, args, **kwargs):
        if self.fail:
            raise OSError("cannot start")
        self.calls.append((args, kwargs))
 
 
@pytest.fixture(autouse=True)
def system(monkeypatch):
    """Pretend every app is installed and nothing is really started."""
    launcher = Launcher()
    monkeypatch.setattr(apps.shutil, "which", lambda cmd: "/usr/bin/" + cmd)
    monkeypatch.setattr(apps.subprocess, "Popen", launcher)
    monkeypatch.setattr(apps, "_protected_pids", lambda: set())
    return launcher
 
 
def use_processes(monkeypatch, procs, stubborn=()):
    fake = FakePsutil(procs, stubborn)
    monkeypatch.setattr(apps, "psutil", fake)
    return fake
 
 
# ------------------------------------------------------------------- open
def test_open_firefox_runs_exact_command_as_a_list(system):
    result = apps.open_application("firefox")
    assert result.success
    assert system.calls[0][0] == ["firefox"]
    assert "shell" not in system.calls[0][1]
    assert "opened" in result.message
 
 
@pytest.mark.parametrize(
    "spoken, command",
    [
        ("browser", "firefox"),
        ("Firefox", "firefox"),
        ("  FIREFOX  ", "firefox"),
        ("terminal", "gnome-terminal"),
        ("calculator", "gnome-calculator"),
        ("files", "nautilus"),
        ("text editor", "gedit"),
        ("فايرفوكس", "firefox"),
        ("المتصفح", "firefox"),
        ("التيرمينال", "gnome-terminal"),
        ("الحاسبة", "gnome-calculator"),
        ("محرر النصوص", "gedit"),
    ],
)
def test_every_allowed_name_maps_to_its_command(spoken, command, system):
    assert apps.open_application(spoken).success
    assert system.calls[-1][0] == [command]
 
 
def test_open_arabic_message(system):
    result = apps.open_application("فايرفوكس", "ar")
    assert result.success
    assert "تم فتح" in result.message
    assert "فايرفوكس" in result.message
 
 
@pytest.mark.parametrize(
    "bad_name",
    ["chrome", "", "   ", "rm", "bash", "firefox; rm -rf /", "firefox && reboot",
     "$(reboot)", "firefox --new-window", "/usr/bin/firefox", "../firefox",
     None, 42],
)
def test_unlisted_or_malicious_names_are_rejected(bad_name, system):
    result = apps.open_application(bad_name)
    assert not result.success
    assert system.calls == []  # nothing was started
 
 
def test_unknown_app_arabic_message(system):
    result = apps.open_application("كروم", "ar")
    assert not result.success
    assert "غير موجود في قائمة" in result.message
 
 
def test_long_unknown_name_is_not_read_out_in_full(system):
    result = apps.open_application("x" * 500)
    assert len(result.message) < 120
 
 
def test_open_when_app_not_installed(monkeypatch, system):
    monkeypatch.setattr(apps.shutil, "which", lambda cmd: None)
    result = apps.open_application("firefox")
    assert not result.success
    assert "not installed" in result.message
    assert system.calls == []
 
 
def test_open_when_launch_fails(system):
    system.fail = True
    result = apps.open_application("firefox")
    assert not result.success
    assert "failed" in result.message
 
 
# ------------------------------------------------------------------ close
def test_close_terminates_only_matching_processes(monkeypatch):
    firefox = FakeProcess(10, "firefox")
    other = FakeProcess(11, "gedit")
    use_processes(monkeypatch, [firefox, other])
    result = apps.close_application("firefox")
    assert result.success
    assert firefox.terminated and not firefox.killed
    assert not other.terminated
    assert "closed" in result.message
 
 
def test_close_handles_all_processes_of_the_app(monkeypatch):
    procs = [FakeProcess(1, "firefox"), FakeProcess(2, "firefox-bin")]
    use_processes(monkeypatch, procs)
    assert apps.close_application("browser").success
    assert all(p.terminated for p in procs)
 
 
def test_close_matches_truncated_linux_process_names(monkeypatch):
    server = FakeProcess(5, "gnome-terminal-")
    calc = FakeProcess(6, "gnome-calculato")
    use_processes(monkeypatch, [server, calc])
    assert apps.close_application("terminal").success
    assert apps.close_application("calculator").success
    assert server.terminated and calc.terminated
 
 
def test_close_kills_a_process_that_refuses_to_stop(monkeypatch):
    stubborn = FakeProcess(20, "firefox")
    use_processes(monkeypatch, [stubborn], stubborn=[20])
    assert apps.close_application("firefox").success
    assert stubborn.terminated and stubborn.killed
 
 
def test_close_app_that_is_not_running(monkeypatch):
    use_processes(monkeypatch, [FakeProcess(1, "gedit")])
    result = apps.close_application("firefox")
    assert not result.success
    assert "not running" in result.message
 
 
def test_close_never_touches_protected_processes(monkeypatch):
    mine = FakeProcess(99, "gnome-terminal-")
    use_processes(monkeypatch, [mine])
    monkeypatch.setattr(apps, "_protected_pids", lambda: {99})
    result = apps.close_application("terminal")
    assert not result.success
    assert not mine.terminated
 
 
def test_close_process_with_no_name_is_ignored(monkeypatch):
    nameless = FakeProcess(7, None)
    use_processes(monkeypatch, [nameless])
    assert not apps.close_application("firefox").success
    assert not nameless.terminated
 
 
@pytest.mark.parametrize("bad_name", ["chrome", "", "systemd", "firefox; reboot", None])
def test_close_rejects_unlisted_names(bad_name, monkeypatch):
    victim = FakeProcess(1, "systemd")
    use_processes(monkeypatch, [victim])
    result = apps.close_application(bad_name)
    assert not result.success
    assert not victim.terminated
 
 
def test_close_arabic_messages(monkeypatch):
    use_processes(monkeypatch, [FakeProcess(1, "firefox")])
    assert "تم إغلاق" in apps.close_application("فايرفوكس", "ar").message
    use_processes(monkeypatch, [])
    assert "لا يعمل" in apps.close_application("فايرفوكس", "ar").message
 
 
def test_close_without_psutil_fails_politely(monkeypatch):
    monkeypatch.setattr(apps, "psutil", None)
    result = apps.close_application("firefox")
    assert not result.success
    assert "failed" in result.message
 