"""Tests for the GUI's non-Tk parts: events, Arabic display, stand-in pipeline.

Run:  pytest tests/test_gui_support.py
(The Tk window itself is covered by the manual GUI checklist in docs/.)
"""
import unittest

from gui import arabic
from gui.events import EXECUTION_STATUSES, TERMINAL_EXECUTION, Event
from gui.standins import StandInPipeline


def run(language, confirm_answer=True, times=1):
    runs = []
    for _ in range(times):
        events = []
        runs.append(events)
    pipeline = StandInPipeline(delay=0)
    out = []
    for events in runs:
        pipeline(events.append, language, lambda prompt: confirm_answer)
        out.append(events)
    return out


class EventTests(unittest.TestCase):
    def test_event_fields(self):
        e = Event("execution", "completed", "Firefox opened")
        self.assertEqual((e.stage, e.state, e.text), ("execution", "completed", "Firefox opened"))

    def test_terminal_statuses_are_known(self):
        self.assertTrue(TERMINAL_EXECUTION <= set(EXECUTION_STATUSES))


class ArabicTests(unittest.TestCase):
    def test_english_and_empty_unchanged(self):
        self.assertEqual(arabic.shape("Show my files"), "Show my files")
        self.assertEqual(arabic.shape(""), "")
        self.assertEqual(arabic.shape(None), "")

    def test_arabic_detected_and_shaping_never_crashes(self):
        self.assertTrue(arabic.has_arabic("اعرض ملفاتي"))
        self.assertTrue(arabic.shape("اعرض ملفاتي\nسطر ثان"))   # returns text either way

    def test_mixed_text_keeps_latin_word(self):
        self.assertIn("report", arabic.shape("احذف report"))


class StandInPipelineTests(unittest.TestCase):
    def stages(self, events):
        return [(e.stage, e.state) for e in events]

    def test_normal_command_completes(self):
        events = run("en")[0]
        self.assertEqual(events[0], Event("listening", "listening"))
        self.assertIn(("execution", "completed"), self.stages(events))
        self.assertEqual(events[-1].stage, "result")

    def test_dangerous_command_confirmed(self):
        events = run("en", True, 2)[1]       # 2nd English demo = DELETE_FILE
        self.assertIn(("execution", "awaiting_confirmation"), self.stages(events))
        self.assertIn(("execution", "completed"), self.stages(events))

    def test_dangerous_command_declined_is_cancelled(self):
        events = run("en", False, 2)[1]
        self.assertIn(("execution", "cancelled"), self.stages(events))
        self.assertNotIn(("execution", "running"), self.stages(events))

    def test_unsupported_command_rejected_never_runs(self):
        events = run("en", True, 3)[2]       # 3rd English demo = UNKNOWN
        self.assertIn(("understanding", "rejected"), self.stages(events))
        self.assertIn(("execution", "rejected"), self.stages(events))
        self.assertNotIn(("execution", "running"), self.stages(events))

    def test_arabic_flow_reports_arabic(self):
        events = run("ar")[0]
        command = next(e for e in events if e.stage == "command")
        self.assertEqual(command.state, "ar")
        self.assertTrue(arabic.has_arabic(command.text))

    def test_unknown_language_defaults_to_english(self):
        command = next(e for e in run("fr")[0] if e.stage == "command")
        self.assertEqual(command.state, "en")


if __name__ == "__main__":
    unittest.main()
