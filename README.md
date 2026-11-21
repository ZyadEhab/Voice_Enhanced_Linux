# 🎙️ Voice-Enhanced Linux (Sound Operating System)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Platform](https://img.shields.io/badge/Platform-Ubuntu%2026.04%20LTS-E95420?style=for-the-badge&logo=ubuntu)
![Course](https://img.shields.io/badge/Course-Operating%20Systems-purple?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Complete-success?style=for-the-badge)
![Tests](https://img.shields.io/badge/Tests-232%20Passed%20%7C%203%20Skipped-brightgreen?style=for-the-badge)

**Voice-Enhanced Linux** is a modular, bilingual (English & Arabic) voice interaction layer designed for **Ubuntu Linux**. It allows users to control operating system tasks—such as file management, application control, and system monitoring—entirely by voice, bridging natural spoken language and Linux system calls through a secure, multi-stage pipeline and dual graphical interfaces (**Tkinter** & **Flet**).

---

## 👥 Team Members & Responsibilities

| # | Role | Name (الاسم) | Student ID | Dept. | Responsibilities |
| :-: | :--- | :--- | :---: | :---: | :--- |
| **1** | **Team Leader & Linux System Environment** | **زياد إيهاب عبد المقصود**<br>*(Zyad Ehab)* | `352400564` | Math & CS | • Prepares Ubuntu, the Python environment, the Shell setup, and file permissions.<br>• Sets up the GitHub repository and the initial documentation.<br>• Leads the team, tracks progress, and sends the weekly reports. |
| **2** | **Command Execution & Validation Engineer** | **محمد سيد محمد الدحداحي**<br>*(Mohamed Sayed Eldhdahy)* | `352400942` | Stat & CS | • Builds the validation layer: allowed intents, safe folders, and confirmation for dangerous actions.<br>• Runs approved operations through subprocess and handles errors.<br>• Implements the process list and CPU, RAM, and disk usage with psutil. |
| **3** | **Speech-to-Text Engineer** | **كريم إبراهيم صلاح الدين**<br>*(Karim Ibrahim)* | `352400827` | Math & CS | • Captures microphone input and records each spoken command.<br>• Integrates faster-whisper for Arabic and English recognition.<br>• Handles recognition errors such as silence or unclear speech. |
| **4** | **Command Understanding / NLP Engineer** | **زياد خالد محمد**<br>*(Zyad Khaled)* | `352400568` | Stat & CS | • Defines the supported intents (e.g. OPEN_APPLICATION, LIST_FILES) and example phrases in both languages.<br>• Integrates the AI model that matches text to an intent and extracts parameters.<br>• Builds the keyword-matching fallback. |
| **5** | **File & Application Management Engineer** | **كريم عمرو محمد**<br>*(Karim Amr)* | `352400832` | Stat & CS | • Implements list, create, rename, and delete for files and folders.<br>• Implements opening and closing of applications.<br>• Returns a clear result message for every operation. |
| **6** | **GUI / UX & Voice Feedback Engineer** | **عبدالرحمن خالد محمد**<br>*(Abdelrahman Khaled)* | `352401468` | Math & CS | • Builds the Tkinter interface: Listen button, listening state, recognized command, result, and history.<br>• Integrates espeak-ng to speak every result in Arabic and English.<br>• Keeps the interface responsive using background threads. |
| **7** | **Testing & Integration Engineer** | **محمد سيد يوسف محمد**<br>*(Mohamed Sayed Youssef)* | `352400943` | Math & CS | • Writes test cases for every feature and records the results.<br>• Merges all modules through GitHub pull requests and fixes integration problems.<br>• Prepares the README and the final demo script. |

---

## ✨ Key Features

- **🌐 Bilingual Voice Interaction:** Full offline support for both **English** and **Arabic** voice commands with spoken audio feedback via `espeak-ng`.
- **⚡ Fast Speech-to-Text (STT):** Powered by pre-warmed `faster-whisper` models for low-latency transcription.
- **🧠 Hybrid NLP Engine:** Combines multilingual semantic embeddings (`sentence-transformers`) with a deterministic keyword-fallback engine. If the AI is unsure, the keyword fallback catches colloquialisms (e.g., Egyptian Arabic like *"شوفلي الملفات"*).
- **🖥️ System Monitoring:** Speak natural commands to check live CPU, RAM, Disk usage, and view the top running processes (powered by `psutil`).
- **📝 Persistent Command History:** Logs every command with its timestamp, recognized intent, and final execution status (Completed, Rejected, Failed).
- **🛡️ Security & Sandboxing:** 
  - **Zero Direct Shell Execution:** Spoken text is never executed directly as a shell command; commands run as validated argument lists.
  - **Strict Whitelisting:** Only explicitly allowed applications and system resources can be accessed.
  - **Multi-Command Guard:** Blocks command chaining and injection characters (`;`, `&`, `and`, `ثم`). *Note: Smartly allows "and" if it's inside a quoted filename like "rock and roll".*
  - **Destructive Action Protection:** Blocks mass-deletion wildcards (`all`, `كل`), blocks command options like `-rf` or `~`, and requires a GUI popup confirmation before deleting files or closing applications.

---

## 🎨 Dual-GUI Architecture (Tkinter & Modern Flet UI)

Because the backend pipeline (`main.py`, `stt/`, `nlp/`, `validation/`, `execution/`, `tts/`) is decoupled from the presentation layer via an event-driven interface (`gui/events.py`), the project supports **two interchangeable frontends**:

1. **Classic Desktop UI (`Tkinter` — Default on `main`):**
   - Lightweight, zero-overhead native desktop interface (`main.py` & `gui/`) with background threading, RTL Arabic reshaping, and a live `Treeview` history log.
2. **Modern Next-Gen UI (`Flet` — Available on [`feat/flet-modern-gui`](../../tree/feat/flet-modern-gui)):**
   - An experimental modern interface (`main_flet.py` & `gui_flet/`) built with **Flet (Flutter for Python)** to elevate the visual experience and usability:
     - **Bilingual RTL/LTR Interface:** Seamless switching between Arabic and English layouts without manual text reshaping hacks.
     - **Real-Time Pipeline Visualizer:** Live step-by-step indicator (`STT ➔ NLP ➔ Validation ➔ Execution ➔ TTS`).
     - **Live System Telemetry & Workspace Explorer:** Built-in CPU/RAM/Disk cards and a safe sandbox file browser (`~/VoiceLinuxWorkspace`).

---

## 🏗️ System Architecture & Pipeline

Every voice command passes through 6 sequential stages orchestrated by `main.py`:

1. **Voice Input (`stt/recorder.py`):** The user presses the **Listen** button and speaks into the microphone.
2. **Speech-to-Text (`stt/transcriber.py`):** The `faster-whisper` model converts the recorded audio into Arabic or English text.
3. **Command Understanding (`nlp/understanding.py`):** The hybrid AI/Keyword engine matches the text to a known intent and extracts required parameters (e.g., `SHOW_SYSTEM_USAGE` -> `resource: cpu`).
4. **Command Validation (`validation/validator.py`):** Checks that the intent and target are whitelisted, ensures paths stay inside `~/VoiceLinuxWorkspace`, and triggers confirmation dialogs for dangerous actions.
5. **Linux Operation (`execution/`):** Runs the approved operation on Ubuntu via Python `os`, `pathlib`, `psutil`, and `subprocess` (`files.py`, `apps.py`, `system_info.py`, `runner.py`).
6. **GUI & Voice Reply (`gui/` or `gui_flet/` & `tts/`):** Displays the result in the active GUI, logs the action in the history view, and speaks the response via `espeak-ng`.

---

## 📂 Project Structure

- `main.py` — Application entry point, model pre-warming & pipeline wiring (Tkinter UI)
- `main_flet.py` — Alternative entry point for the modern Flet UI *(on `feat/flet-modern-gui`)*
- `stt/` — Audio capture (`recorder.py`), Whisper transcription (`transcriber.py`), evaluation (`evaluate.py`, `metrics.py`) & vocabulary (`vocabulary.py`)
- `nlp/` — Intent definitions (`intents.py`) and hybrid semantic/keyword understanding (`understanding.py`)
- `validation/` — Security checks, path sandboxing & parameter validation (`validator.py`)
- `execution/` — OS operations: file handling (`files.py`), app control (`apps.py`), system metrics (`system_info.py`) & runner (`runner.py`)
- `gui/` — Classic Tkinter desktop app (`app.py`), Arabic reshaping (`arabic.py`), shared events (`events.py`) & stand-ins (`standins.py`)
- `gui_flet/` — Modern bilingual Flet UI components & dashboard *(on `feat/flet-modern-gui`)*
- `tts/` — Offline bilingual Text-to-Speech voice feedback (`speaker.py`)
- `tests/` — Comprehensive `pytest` suite (`test_stt.py`, `test_nlp.py`, `test_validation_execution.py`, `test_files.py`, `test_apps.py`, `test_gui_support.py`, `test_tts.py`, `test_runner_integration.py`)
- `setup_env.sh` & `requirements.txt` — Automated environment setup script and Python dependencies

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
| **Audio Capture** | `sounddevice` | Records microphone input |
| **Speech-to-Text** | `faster-whisper` (`small`) | Offline bilingual speech recognition |
| **NLP / Embeddings** | `sentence-transformers` | Multilingual semantic intent matching (`paraphrase-multilingual-MiniLM-L12-v2`) |
| **OS & Process API** | `subprocess`, `psutil`, `pathlib` | Safe command execution, file handling & system metrics |
| **Text-to-Speech** | `espeak-ng` | Offline Arabic & English voice feedback |
| **Graphical UI (Primary)** | `Tkinter` (`arabic-reshaper`, `python-bidi`) | Lightweight desktop GUI with background threading & RTL Arabic support |
| **Graphical UI (Modern)** | `Flet` *(on `feat/flet-modern-gui`)* | Modern RTL/LTR dashboard, live pipeline visualizer & telemetry |
| **Testing** | `pytest` | Unit and integration test suite |

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you are running **Ubuntu Linux** with Python 3.8+ and required system packages installed:

    sudo apt update
    sudo apt install python3-pip python3-venv python3-tk portaudio19-dev espeak-ng -y

### 2. Installation
Clone the repository and run the setup script (or install via `venv`):

    git clone https://github.com/ZyadEhab/Voice_Enhanced_Linux.git
    cd Voice_Enhanced_Linux
    chmod +x setup_env.sh
    ./setup_env.sh

*(Alternatively, manual setup):*

    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

### 3. Running the Application

**Option A — Classic Tkinter GUI (`main` branch):**

    python3 main.py

**Option B — Modern Flet GUI (`feat/flet-modern-gui` branch):**

    git checkout feat/flet-modern-gui
    pip install flet
    python3 main_flet.py

*Note: On launch, the system pre-warms the STT and NLP models in the background. Once the status badge turns green (**Ready**), click **Listen** and speak your command.*

### 4. Running Tests
We have a comprehensive test suite covering all modules (NLP, Validation, Execution, GUI, and STT mocks). To run all tests, execute:

    python -m pytest -v

*(Expected output: 232 passed, 3 skipped)*
