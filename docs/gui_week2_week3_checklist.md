# GUI + Voice Feedback: Week 2 and Week 3 (Abdelrahman Khaled Mohamed)

## Run

```bash
sudo apt install python3-tk espeak-ng espeak-ng-data
pip install arabic-reshaper python-bidi pytest
python -m gui.app            # demo with stand-in modules
pytest tests/test_tts.py tests/test_gui_support.py
```

## Files (all inside my own folders, Section 10.0)

| File | Purpose |
|---|---|
| `gui/app.py` | Tkinter window, queue polling, worker threads, confirmation dialog, history |
| `gui/events.py` | `Event(stage, state, text)` and the event vocabulary |
| `gui/arabic.py` | Arabic reshaper + bidi for display only |
| `gui/standins.py` | Stand-in pipeline so the GUI works before the real modules |
| `tts/speaker.py` | `speak(message, language)` with espeak-ng, `stop()`, `is_available()` |
| `tests/test_tts.py`, `tests/test_gui_support.py` | Automated tests (mocked, no audio, no display) |

## Plugging in the real pipeline

`App(root, pipeline=...)` takes any callable `pipeline(emit, language, confirm)`.
Run it in the worker thread, send `Event`s with `emit`, and call `confirm(prompt)`
when validation says `needs_confirmation`. Event vocabulary: see `gui/events.py`.

## OS concepts for the report

- **Threads:** pipeline thread per Listen press + one TTS thread; the GUI thread only reads a thread-safe queue with `after()`.
- **Process management:** espeak-ng is a child process (`Popen`), stopped with `terminate()`.
- **Shell / permissions:** argument list, no `shell=True`, text through stdin; the GUI only displays and triggers.
- **I/O redirection:** espeak-ng stdout/stderr go to `/dev/null`.
- **User interface:** state, command, understanding, execution status, result, history.

## Manual GUI checklist (record pass/fail)

| # | Check | Expected | Result |
|---|---|---|---|
| G-01 | Open window, resize smaller | Minimum 900x600 enforced | |
| G-02 | Press Listen | State: Listening -> Processing -> Speaking -> Ready; button disabled until Ready | |
| G-03 | Move/resize window while Listening | Window stays responsive | |
| G-04 | Press Listen twice quickly | Second press ignored | |
| G-05 | EN command (Show my files) | Command, intent, Completed, result text, spoken reply | |
| G-06 | Delete demo, answer Yes | Confirmation dialog; Completed | |
| G-07 | Delete demo, answer No | Cancelled; nothing runs | |
| G-08 | Delete demo, wait 10 s | Auto-cancel; status Cancelled | |
| G-09 | Close the dialog with X | Treated as No | |
| G-10 | Unsupported command demo | Rejected, spoken explanation | |
| G-11 | Switch to AR, press Listen | Arabic command and result display correctly (right-to-left, joined letters) | |
| G-12 | Arabic reply spoken | Arabic voice is used | |
| G-13 | Untick Voice reply | No speech; text still shown; running speech stops | |
| G-14 | espeak-ng not installed | App runs, status bar says "espeak-ng missing", no crash | |
| G-15 | Several commands | History has one row each, newest first | |
| G-16 | Close window while speaking | Window closes, speech stops | |
