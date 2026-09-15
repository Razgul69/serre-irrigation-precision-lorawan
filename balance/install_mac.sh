#!/bin/bash
# Installation du collecteur balance sur macOS.
# Usage : bash install_mac.sh
set -e

echo "=== Collecteur balance Ohaus - installation macOS ==="

# 1. Python 3 requis
if ! command -v python3 >/dev/null; then
    echo "Python 3 absent. macOS va proposer d'installer les outils en ligne"
    echo "de commande : accepter, puis relancer ce script."
    xcode-select --install || true
    exit 1
fi
echo "Python : $(python3 --version)"

# 2. Environnement virtuel dedie
APPDIR="$HOME/BalanceCollecteur"
mkdir -p "$APPDIR"
cd "$APPDIR"
if [ ! -d venv ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet pyserial pyinstaller

# 3. Recuperation du script de collecte
SCRIPT_URL="https://raw.githubusercontent.com/Razgul69/serre-irrigation-precision-lorawan/master/balance/balance_gui_macos.py"
curl -fsSL "$SCRIPT_URL" -o balance_gui_macos.py
echo "Script telecharge."

# 4. Construction de l'application
python3 -m PyInstaller --windowed --noconfirm --name BalanceCollecteurMac balance_gui_macos.py

# Forcer le mode clair : l'interface est concue pour un fond blanc
/usr/libexec/PlistBuddy -c "Add :NSRequiresAquaSystemAppearance bool true" \
    dist/BalanceCollecteurMac.app/Contents/Info.plist 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :NSRequiresAquaSystemAppearance true" \
    dist/BalanceCollecteurMac.app/Contents/Info.plist

# 5. Installation dans /Applications de l'utilisateur
mkdir -p "$HOME/Applications"
rm -rf "$HOME/Applications/BalanceCollecteurMac.app"
cp -R dist/BalanceCollecteurMac.app "$HOME/Applications/"

echo ""
echo "=== Installation terminee ==="
echo "Application : $HOME/Applications/BalanceCollecteurMac.app"
echo "Donnees CSV : $HOME/Documents/BalanceCollecteur/data balance/"
echo "Brancher la balance USB avant de lancer l'application."
