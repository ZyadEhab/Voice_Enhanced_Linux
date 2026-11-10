# 🎙️ Voice-Enhanced Linux (Sound Operating System)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Platform](https://img.shields.io/badge/Platform-Ubuntu%2026.04%20LTS-E95420?style=for-the-badge&logo=ubuntu)
![Course](https://img.shields.io/badge/Course-Operating%20Systems-purple?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)

**Voice-Enhanced Linux** is a modular, bilingual (English & Arabic) voice interaction layer designed for **Ubuntu Linux**. It allows users to control operating system tasks—such as file management, application control, and system monitoring—entirely by voice, bridging natural spoken language and Linux system calls through a secure, multi-stage pipeline and a responsive graphical interface.

---

## 👥 Team Members & Responsibilities

| # | Name (الاسم) | Student ID | Dept. | Role | Key Responsibilities |
| :-: | :--- | :---: | :---: | :--- | :--- |
| **1** | **زياد إيهاب عبد المقصود أمين**<br>*(Zyad Ehab Abd El-Maksoud)* | `352400564` | Math & CS | **Team Leader & Linux System Environment** | • Prepares Ubuntu environment, Python setup (`setup_env.sh`), Shell configuration & file permissions.<br>• Orchestrates main pipeline integration (`main.py`), manages GitHub repository, tracks progress & compiles reports. |
| **2** | **محمد سيد محمد الدحداحي**<br>*(Mohamed Sayed El-Dahdahy)* | `352400942` | Math & CS | **Speech-to-Text (STT) Engineer** | • Captures microphone audio input using `sounddevice` (`stt/recorder.py`).<br>• Integrates `faster-whisper` (Whisper "small" model) for offline Arabic & English recognition (`stt/transcriber.py`).<br>• Handles audio errors such as silence or unclear speech. |
| **3** | **زياد خالد محمد**<br>*(Zyad Khaled Mohamed)* | `352400568` | Stat & CS | **Command Understanding / NLP Engineer** | • Defines the 9 core intents and bilingual training phrases (`nlp/intents.py`).<br>• Integrates `sentence-transformers` (`paraphrase-multilingual-MiniLM-L12-v2`) for semantic intent matching & parameter extraction (`nlp/understanding.py`).<br>• Builds the deterministic keyword-matching fallback engine. |
| **4** | **كريم إبراهيم صلاح الدين**<br>*(Karim Ibrahim Salah El-Din)* | `352400827` | Math & CS | **Command Execution & Validation Engineer** | • Builds the security validation layer (`validation/validator.py`): allowed intents, safe workspace paths & confirmation checks.<br>• Executes approved operations safely via `execution/runner.py` without shell injection.<br>• Implements process listing and CPU, RAM, and disk monitoring via `psutil` (`execution/system_info.py`). |
| **5** | **كريم عمرو محمد**<br>*(Karim Amr Mohamed)* | `352400832` | Stat & CS | **File & Application Management Engineer** | • Implements file & folder operations (`list`, `create`, `rename`, `delete`) inside the safe workspace (`execution/files.py`).<br>• Implements launching and closing of whitelisted Ubuntu applications (`execution/apps.py`).<br>• Returns structured result messages for every OS action. |
| **6** | **عبدالرحمن خالد محمد**<br>*(Abdelrahman Khaled Mohamed)* | `352401468` | Stat & CS | **GUI / UX & Voice Feedback Engineer** | • Builds the `Tkinter` desktop interface (`gui/app.py`, `gui/arabic.py`): Listen button, live status badge, recognized command, output view & command history.<br>• Integrates `espeak-ng` for offline Arabic & English voice replies (`tts/speaker.py`).<br>• Maintains UI responsiveness using background threads. |
| **7** | **محمد سيد يوسف محمد**<br>*(Mohamed Sayed Youssef)* | `352400943` | Math & CS | **Testing & Integration Engineer** | • Writes and executes `pytest` test cases across all modules (`tests/`) and logs results.<br>• Reviews and merges modules via GitHub Pull Requests and resolves integration issues.<br>• Prepares documentation and final demo testing workflows. |

---

## ✨ Key Features

* **🌐 Bilingual Voice Interaction:** Full offline support for both **English** and **Arabic** voice commands with spoken audio feedback via `espeak-ng`.
* **⚡ Fast Speech-to-Text (STT):** Powered by pre-warmed `faster-whisper` models for low-latency transcription.
* **🧠 Hybrid NLP Engine:** Combines multilingual semantic embeddings (`sentence-transformers`) with a deterministic keyword-fallback engine for reliable intent classification and parameter extraction.
* **🛡️ Security & Sandboxing:** 
  * **Zero Direct Shell Execution:** Spoken text is never executed directly as a shell command; commands run as validated argument lists.
  * **Strict Whitelisting:** Only explicitly allowed applications and system resources can be accessed.
  * **Multi-Command Guard:** Blocks command chaining and injection characters (`;`, `&`, `and`, `ثم`).
  * **Destructive Action Protection:** Blocks mass-deletion wildcards (`all`, `كل`) and requires user confirmation before deleting files or closing applications.
* **🖥️ Modern Tkinter GUI:** Displays live status (`Ready`, `Listening`, `Completed`, `Rejected`), recognized text, extracted intents, execution results, and a persistent **Command History** log.

---

## 🏗️ System Architecture & Pipeline

Every voice command passes through 6 sequential stages orchestrated by `main.py`:

1. **Voice Input (`stt/recorder.py`):** The user presses the **Listen** button and speaks into the microphone.
2. **Speech-to-Text (`stt/transcriber.py`):** The `faster-whisper` model converts the recorded audio into Arabic or English text.
3. **Command Understanding (`nlp/understanding.py`):** The hybrid AI/Keyword engine matches the text to a known intent and extracts required parameters (e.g., `OPEN_APPLICATION` -> `firefox`).
4. **Command Validation (`validation/validator.py`):** Checks that the intent and target are whitelisted, ensures paths stay inside `~/VoiceLinuxWorkspace`, and triggers confirmation dialogs for dangerous actions.
5. **Linux Operation (`execution/`):** Runs the approved operation on Ubuntu via Python `os`, `pathlib`, `psutil`, and `subprocess` (`files.py`, `apps.py`, `system_info.py`, `runner.py`).
6. **GUI & Voice Reply (`gui/` & `tts/`):** Displays the result in the `Tkinter` interface, logs the action in the history table, and speaks the response via `espeak-ng`.

---

## 📂 Project Structure

* `main.py` — Application entry point, model pre-warming & pipeline wiring
* `stt/` — Audio capture (`recorder.py`), Whisper transcription (`transcriber.py`), evaluation (`evaluate.py`, `metrics.py`) & vocabulary (`vocabulary.py`)
* `nlp/` — Intent definitions (`intents.py`) and hybrid semantic/keyword understanding (`understanding.py`)
* `validation/` — Security checks, path sandboxing & parameter validation (`validator.py`)
* `execution/` — OS operations: file handling (`files.py`), app control (`apps.py`), system metrics (`system_info.py`) & runner (`runner.py`)
* `gui/` — Tkinter desktop app (`app.py`), Arabic reshaping (`arabic.py`), events (`events.py`) & stand-ins (`standins.py`)
* `tts/` — Offline bilingual Text-to-Speech voice feedback (`speaker.py`)
* `tests/` — Comprehensive `pytest` suite (`test_stt.py`, `test_nlp.py`, `test_validation_execution.py`, `test_files.py`, `test_apps.py`, `test_gui_support.py`, `test_tts.py`, `test_runner_integration.py`)
* `setup_env.sh` & `requirements.txt` — Automated environment setup script and Python dependencies

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
| **Graphical UI** | `Tkinter` (`arabic-reshaper`, `python-bidi`) | Desktop GUI with background threading & RTL Arabic support |
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

    python3 main.py

*Note: On launch, the system pre-warms the STT and NLP models in the background. Once the status badge turns green (**Ready**), click **Listen** and speak your command.*

### 4. Running Tests

    pytest
