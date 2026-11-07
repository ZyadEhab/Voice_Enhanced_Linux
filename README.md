# Voice-Enhanced Linux

A modular Voice Interaction Layer on top of Ubuntu Linux supporting English and Arabic voice commands.

## Architecture Pipeline
User -> Microphone (sounddevice) -> Speech-to-Text (faster-whisper) -> Command Understanding (NLP) -> Command Validation -> Linux Operation -> Result -> Text-to-Speech (espeak-ng) -> Tkinter GUI

## Project Structure
- stt/ : Speech-to-text (microphone capture and faster-whisper)
- nlp/ : Command understanding (intents, example phrases, semantic & keyword matching)
- validation/ : Allowed intents, safe working folder (~/VoiceLinuxWorkspace), confirmation rules
- execution/ : Linux operations (files, applications, processes, system usage)
- tts/ : Text-to-speech replies in English and Arabic (espeak-ng)
- gui/ : Tkinter interface
- tests/ : Automated unit and integration tests (pytest)
- docs/ : Project reports, GUI layouts, and diagrams

## Environment Setup (Ubuntu)
sudo apt update
sudo apt install python3-pip python3-venv python3-tk espeak-ng libportaudio2 ffmpeg -y
pip3 install -r requirements.txt --break-system-packages
