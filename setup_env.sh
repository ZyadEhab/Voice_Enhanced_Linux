#!/usr/bin/env bash
# Team Leader & Linux System Environment Setup Script
set -e

WORKSPACE="$HOME/VoiceLinuxWorkspace"
echo "[Environment] Creating safe workspace at $WORKSPACE with mode 700..."
mkdir -p "$WORKSPACE"
chmod 700 "$WORKSPACE"
ls -ld "$WORKSPACE"

echo "[Environment] Checking required Ubuntu packages..."
sudo apt update
sudo apt install -y python3-pip python3-venv python3-tk espeak-ng libportaudio2 ffmpeg

echo "[Environment] Installing Python dependencies..."
pip3 install -r requirements.txt --break-system-packages
echo "[Environment] Setup complete."
