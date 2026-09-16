#!/bin/zsh
set -e
cd "$(dirname "$0")/.."
python3 -m venv .venv-macos
source .venv-macos/bin/activate
python -m pip install --upgrade pip pyserial pyinstaller
python -m PyInstaller --windowed --name BalanceCollecteurMac --distpath . --workpath build-macos --specpath build-macos balance/balance_gui_macos.py