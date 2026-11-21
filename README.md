# 🎙️ Voice-Enhanced Linux — Modern Flet UI (`feat/flet-modern-gui`)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Platform](https://img.shields.io/badge/Platform-Ubuntu%2026.04%20LTS-E95420?style=for-the-badge&logo=ubuntu)
![UI](https://img.shields.io/badge/Frontend-Flet%20Modern%20UI-02569B?style=for-the-badge&logo=flutter)
![Course](https://img.shields.io/badge/Course-Operating%20Systems-purple?style=for-the-badge)
![Tests](https://img.shields.io/badge/Tests-232%20Passed%20%7C%203%20Skipped-brightgreen?style=for-the-badge)

**Voice-Enhanced Linux** is a modular, bilingual (English & Arabic) voice interaction layer designed for **Ubuntu Linux**. This branch (`feat/flet-modern-gui`) hosts the **next-generation modern graphical interface built with Flet**, providing an upgraded visual experience, native bilingual RTL/LTR layout switching, live system telemetry, and a real-time pipeline visualizer on top of our secure Linux voice pipeline.

> **Note:** Looking for the classic lightweight Tkinter desktop interface? Switch to the [`main`](../../tree/main) branch.

---

## 👥 Team Members & Responsibilities

| # | Role | Name (الاسم) | Student ID | Dept. | Responsibilities |
| :-: | :--- | :--- | :---: | :---: | :--- |
| **1** | **Team Leader & Linux System Environment** | **زياد إيهاب عبد المقصود**<br>*(Zyad Ehab)* | `352400564` | Math & CS | • Prepares Ubuntu, the Python environment, the Shell setup, and file permissions.<br>• Sets up the GitHub repository, orchestrates the main pipeline, and leads the modern Flet UI integration.<br>• Leads the team, tracks progress, and sends the weekly reports. |
| **2** | **Command Execution & Validation Engineer** | **محمد سيد محمد الدحداحي**<br>*(Mohamed Sayed Eldhdahy)* | `352400942` | Stat & CS | • Builds the validation layer: allowed intents, safe folders, and confirmation for dangerous actions.<br>• Runs approved operations through subprocess and handles errors.<br>• Implements the process list and CPU, RAM, and disk usage with psutil. |
| **3** | **Speech-to-Text Engineer** | **كريم إبراهيم صلاح الدين**<br>*(Karim Ibrahim)* | `352400827` | Math & CS | • Captures microphone input and records each spoken command.<br>• Integrates faster-whisper for Arabic and English recognition.<br>• Handles recognition errors such as silence or unclear speech. |
| **4** | **Command Understanding / NLP Engineer** | **زياد خالد محمد**<br>*(Zyad Khaled)* | `352400568` | Stat & CS | • Defines the supported intents (e.g. OPEN_APPLICATION, LIST_FILES) and example phrases in both languages.<br>• Integrates the AI model that matches text to an intent and extracts parameters.<br>• Builds the keyword-matching fallback. |
| **5** | **File & Application Management Engineer** | **كريم عمرو محمد**<br>*(Karim Amr)* | `352400832` | Stat & CS | • Implements list, create, rename, and delete for files and folders.<br>• Implements opening and closing of applications.<br>• Returns a clear result message for every operation. |
| **6** | **GUI / UX & Voice Feedback Engineer** | **عبدالرحمن خالد محمد**<br>*(Abdelrahman Khaled)* | `352401468` | Math & CS | • Builds the classic Tkinter interface: Listen button, listening state, recognized command, result, and history.<br>• Integrates espeak-ng to speak every result in Arabic and English.<br>• Keeps the interface responsive using background threads. |
| **7** | **Testing & Integration Engineer** | **محمد سيد يوسف محمد**<br>*(Mohamed Sayed Youssef)* | `352400943` | Math & CS | • Writes test cases for every feature and records the results.<br>• Merges all modules through GitHub pull requests and fixes integration problems.<br>• Prepares the README and the final demo script. |

---

## ✨ What's New in the Modern Flet UI (`feat/flet-modern-gui`)

- **🎨 Modern Dashboard & Glassmorphism Cards:** Clean, responsive desktop layout powered by **Flet (Flutter for Python)**.
- **🔄 Native Bilingual RTL / LTR Switching:** Instant toggle between English (LTR) and Arabic (RTL) layouts without manual text reshaping hacks.
- **⚡ Real-Time Pipeline Visualizer:** Live step-by-step status indicator showing each stage (`STT ➔ NLP ➔ Validation ➔ Execution ➔ TTS`) as your voice command is processed.
- **📊 Live System Telemetry & Quick Chips:** Real-time CPU, RAM, and Disk resource counters alongside bilingual quick-command chips.
- **🛡️ Full Security & Sandboxing Parity:** Shares the exact same `validation/` and `execution/` backend as `main`—zero direct shell execution, strict whitelisting, multi-command guard, and confirmation modals for destructive actions (`DELETE_FILE`, `CLOSE_APPLICATION`).

---

## 🏗️ System Architecture & Pipeline

Every voice command passes through 6 sequential stages orchestrated by `main_flet.py`:

1. **Voice Input (`stt/recorder.py`):** The user presses the **Listen** button (or clicks a quick command chip) and speaks into the microphone.
2. **Speech-to-Text (`stt/transcriber.py`):** The `faster-whisper` model converts the recorded audio into Arabic or English text.
3. **Command Understanding (`nlp/understanding.py`):** The hybrid AI/Keyword engine matches the text to a known intent and extracts required parameters (e.g., `SHOW_SYSTEM_USAGE` -> `resource: cpu`).
4. **Command Validation (`validation/validator.py`):** Checks that the intent and target are whitelisted, ensures paths stay inside `~/VoiceLinuxWorkspace`, and triggers confirmation dialogs for dangerous actions.
5. **Linux Operation (`execution/`):** Runs the approved operation on Ubuntu via Python `os`, `pathlib`, `psutil`, and `subprocess` (`files.py`, `apps.py`, `system_info.py`, `runner.py`).
6. **Flet UI & Voice Reply (`gui_flet/` & `tts/`):** Updates the live pipeline visualizer, displays the result card, logs the action in history, and speaks the response via `espeak-ng`.

---

## 📂 Project Structure

- `main_flet.py` — **Primary entry point for the Modern Flet GUI**
- `main.py` — Classic Tkinter entry point (maintained for backward compatibility)
- `gui_flet/` — Modern bilingual Flet UI components, cards, telemetry & pipeline visualizer
- `gui/` — Classic Tkinter desktop app (`app.py`), Arabic reshaping (`arabic.py`), shared events (`events.py`) & stand-ins (`standins.py`)
- `stt/` — Audio capture (`recorder.py`), Whisper transcription (`transcriber.py`), evaluation (`evaluate.py`, `metrics.py`) & vocabulary (`vocabulary.py`)
- `nlp/` — Intent definitions (`intents.py`) and hybrid semantic/keyword understanding (`understanding.py`)
- `validation/` — Security checks, path sandboxing & parameter validation (`validator.py`)
- `execution/` — OS operations: file handling (`files.py`), app control (`apps.py`), system metrics (`system_info.py`) & runner (`runner.py`)
- `tts/` — Offline bilingual Text-to-Speech voice feedback (`speaker.py`)
- `tests/` — Comprehensive `pytest` suite (`test_stt.py`, `test_nlp.py`, `test_validation_execution.py`, `test_files.py`, `test_apps.py`, `test_gui_support.py`, `test_tts.py`, `test_runner_integration.py`)
- `setup_env.sh` & `requirements.txt` — Automated environment setup script and Python dependencies (including `flet`)

---

## 🎯 Supported Commands (9 Core Intents)

| Category | Intent | English Example | Arabic Example | Confirmation Required? |
| :--- | :--- | :--- | :--- | :---: |
| **Files & Folders** | `LIST_FILES` | *"Show my files"* | *"اعرض الملفات"* | No |
| | `CREATE_FILE` | *"Create file test.txt"* | *"انشئ ملف test.txt"* | No |
| | `CREATE_FOLDER` | *"Create folder docs"* | *"انشئ مجلد جديد docs"* | No |
| | `RENAME_FILE` | *"Rename notes to report"* | *"غير اسم notes إلى report"* | No |
| | `DELETE_FILE` | *"Delete file test.txt"* | *"احذف الملف test.txt"* | **Yes** ⚠️ |
| **Applications** | `OPEN_APPLICATION` | *"Open Firefox"* / *"Open Calculator"* | *"افتح فايرفوكس"* / *"افتح الحاسبة"* | No |
| | `CLOSE_APPLICATION` | *"Close Firefox"* / *"Close Terminal"* | *"اغلق فايرفوكس"* / *"اقفل المتصفح"* | **Yes** ⚠️ |
| **System Monitor**| `SHOW_PROCESSES` | *"Show running processes"* | *"اعرض العمليات الجارية"* | No |
| | `SHOW_SYSTEM_USAGE` | *"Show CPU usage"* / *"Memory usage"* | *"استخدام المعالج"* / *"كم الذاكرة المستخدمة"* | No |

---

## 🛠️ Tech Stack

| Component | Technology / Tool | Purpose |
| :--- | :--- | :--- |
| **Operating System** | Ubuntu 26.04.1 LTS | Open-source Linux environment |
| **Language** | Python 3 | Core programming language for all modules |
| **Modern Graphical UI** | `Flet` | Modern RTL/LTR dashboard, live pipeline visualizer & telemetry |
| **Classic Graphical UI** | `Tkinter` (`arabic-reshaper`, `python-bidi`) | Fallback lightweight desktop GUI |
| **Audio Capture** | `sounddevice` | Records microphone input |
| **Speech-to-Text** | `faster-whisper` (`small`) | Offline bilingual speech recognition |
| **NLP / Embeddings** | `sentence-transformers` | Multilingual semantic intent matching (`paraphrase-multilingual-MiniLM-L12-v2`) |
| **OS & Process API** | `subprocess`, `psutil`, `pathlib` | Safe command execution, file handling & system metrics |
| **Text-to-Speech** | `espeak-ng` | Offline Arabic & English voice feedback |
| **Testing** | `pytest` | Unit and integration test suite |

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you are running **Ubuntu Linux** with Python 3.8+ and required system packages installed:

    sudo apt update
    sudo apt install python3-pip python3-venv python3-tk portaudio19-dev espeak-ng libmpv-dev -y

### 2. Installation (Flet Branch)
Clone the repository, switch to `feat/flet-modern-gui`, and install dependencies (including `flet`):

    git clone https://github.com/ZyadEhab/Voice_Enhanced_Linux.git
    cd Voice_Enhanced_Linux
    git checkout feat/flet-modern-gui
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

### 3. Running the Modern Flet Application

    python3 main_flet.py

*(To launch the classic Tkinter version instead, run `python3 main.py`.)*

### 4. Running Tests

    python -m pytest -v

*(Expected output: 232 passed, 3 skipped)*
