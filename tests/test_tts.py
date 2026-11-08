"""Tests for tts/speaker.py (no real audio: subprocess is mocked).

Run:  pytest tests/test_tts.py
"""
import subprocess
import unittest
from unittest import mock

from tts import speaker


class FakeProc:
    def __init__(self, returncode=0, raise_timeout=False):
        self.returncode = returncode
        self.raise_timeout = raise_timeout
        self.sent = None
        self.killed = False

    def communicate(self, data=None, timeout=None):
        if self.raise_timeout and not self.killed:
            raise subprocess.TimeoutExpired("espeak-ng", timeout)
        self.sent = data
        return (None, None)

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed = True

    def terminate(self):
        self.killed = True


class SpeakTests(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(speaker.shutil, "which", return_value="/usr/bin/espeak-ng")
        p.start()
        self.addCleanup(p.stop)

    def _speak(self, message, language="en", proc=None):
        proc = proc or FakeProc()
        with mock.patch.object(speaker.subprocess, "Popen", return_value=proc) as popen:
            ok = speaker.speak(message, language)
        return ok, popen, proc

    def test_english_voice_and_text_via_stdin(self):
        ok, popen, proc = self._speak("The browser was opened.", "en")
        self.assertTrue(ok)
        args = popen.call_args.args[0]
        self.assertEqual(args[:3], ["espeak-ng", "-v", "en-us"])
        self.assertEqual(proc.sent, b"The browser was opened.")

    def test_arabic_voice_and_utf8(self):
        ok, popen, proc = self._speak("تم فتح المتصفح", "ar")
        self.assertTrue(ok)
        self.assertIn("ar", popen.call_args.args[0])
        self.assertEqual(proc.sent.decode("utf-8"), "تم فتح المتصفح")

    def test_unknown_language_falls_back_to_english(self):
        _, popen, _ = self._speak("hello", "fr")
        self.assertIn("en-us", popen.call_args.args[0])

    # --- security cases -------------------------------------------------------
    def test_no_shell_and_message_not_in_arguments(self):
        evil = "; rm -rf / && echo pwned"
        _, popen, proc = self._speak(evil)
        self.assertIsInstance(popen.call_args.args[0], list)
        self.assertNotIn("shell", popen.call_args.kwargs)          # never shell=True
        self.assertNotIn(evil, popen.call_args.args[0])            # text only in stdin
        self.assertEqual(proc.sent, evil.encode())

    def test_text_starting_with_dash_cannot_become_an_option(self):
        _, popen, proc = self._speak("--help -v zz")
        self.assertEqual(popen.call_args.args[0][-1], "--stdin")
        self.assertEqual(proc.sent, b"--help -v zz")

    def test_output_is_discarded(self):
        _, popen, _ = self._speak("hi")
        self.assertEqual(popen.call_args.kwargs["stderr"], subprocess.DEVNULL)
        self.assertEqual(popen.call_args.kwargs["stdout"], subprocess.DEVNULL)

    # --- error cases ----------------------------------------------------------
    def test_empty_and_none_message_not_spoken(self):
        for message in ("", "   \n\t", None):
            ok, popen, _ = self._speak(message)
            self.assertFalse(ok)
            popen.assert_not_called()

    def test_control_characters_removed_and_length_bounded(self):
        _, _, proc = self._speak("a\x00b\x07c\n\nd")
        self.assertEqual(proc.sent, b"a b c d")
        _, _, proc = self._speak("x" * 5000)
        self.assertEqual(len(proc.sent), speaker.MAX_CHARS)

    def test_missing_espeak_returns_false_without_crashing(self):
        with mock.patch.object(speaker.shutil, "which", return_value=None):
            self.assertFalse(speaker.speak("hello"))

    def test_start_failure_returns_false(self):
        with mock.patch.object(speaker.subprocess, "Popen", side_effect=OSError):
            self.assertFalse(speaker.speak("hello"))

    def test_nonzero_exit_returns_false(self):
        ok, _, _ = self._speak("hello", proc=FakeProc(returncode=1))
        self.assertFalse(ok)

    def test_timeout_kills_process(self):
        proc = FakeProc(raise_timeout=True)
        ok, _, _ = self._speak("hello", proc=proc)
        self.assertFalse(ok)
        self.assertTrue(proc.killed)

    def test_stop_when_idle_is_safe(self):
        speaker.stop()


if __name__ == "__main__":
    unittest.main()
