#!/bin/bash
# Installation du collecteur balance sur macOS.
# Usage : bash install_mac.sh
set -e

echo "=== Collecteur balance Ohaus - installation macOS ==="

# 1. Python avec Tk >= 8.6 requis (le Tk 8.5 systeme affiche une fenetre noire)
tk_ok() {
    "$1" -c 'import tkinter,sys; sys.exit(0 if tkinter.TkVersion >= 8.6 else 1)' 2>/dev/null
}

PYBIN=""
for cand in /Library/Frameworks/Python.framework/Versions/3.*/bin/python3 \
            /usr/local/bin/python3 /opt/homebrew/bin/python3 python3; do
    if command -v "$cand" >/dev/null 2>&1 && tk_ok "$cand"; then
        PYBIN="$(command -v "$cand")"
        break
    fi
done

if [ -z "$PYBIN" ]; then
    echo "Aucun Python avec Tk 8.6 trouve : installation de Python 3.12 (python.org)."
    echo "Le mot de passe administrateur du Mac sera demande."
    PKG="/tmp/python-3.12.10-macos11.pkg"
    curl -fsSL "https://www.python.org/ftp/python/3.12.10/python-3.12.10-macos11.pkg" -o "$PKG"
    sudo installer -pkg "$PKG" -target /
    PYBIN="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
fi
echo "Python : $($PYBIN --version) ($PYBIN)"

# 2. Environnement virtuel dedie (reconstruit si le Python a change)
APPDIR="$HOME/BalanceCollecteur"
mkdir -p "$APPDIR"
cd "$APPDIR"
if [ ! -x venv/bin/python3 ] || ! tk_ok venv/bin/python3; then
    rm -rf venv
    "$PYBIN" -m venv venv
fi
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet pyserial

# 3. Recuperation du script de collecte
SCRIPT_URL="https://raw.githubusercontent.com/Razgul69/serre-irrigation-precision-lorawan/master/balance/balance_gui_macos.py"
curl -fsSL "$SCRIPT_URL" -o balance_gui_macos.py
curl -fsSL "https://raw.githubusercontent.com/Razgul69/serre-irrigation-precision-lorawan/master/balance/diagnose_serial_macos.py" \
    -o diagnose_serial_macos.py
echo "Script telecharge."

# 4. Bundle .app construit a la main : PyInstaller exige lipo/xcrun (outils Xcode)
APP="$HOME/Applications/BalanceCollecteurMac.app"
mkdir -p "$HOME/Applications"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>BalanceCollecteurMac</string>
    <key>CFBundleDisplayName</key><string>Balance Ohaus</string>
    <key>CFBundleIdentifier</key><string>org.ird.balancecollecteur</string>
    <key>CFBundleVersion</key><string>1.0</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleExecutable</key><string>launcher</string>
    <key>NSHighResolutionCapable</key><true/>
    <key>NSRequiresAquaSystemAppearance</key><true/>
</dict>
</plist>
PLIST

cat > "$APP/Contents/MacOS/launcher" <<LAUNCHER
#!/bin/bash
cd "$APPDIR"
exec "$APPDIR/venv/bin/python" "$APPDIR/balance_gui_macos.py"
LAUNCHER
chmod +x "$APP/Contents/MacOS/launcher"

echo ""
echo "=== Installation terminee ==="
echo "Application : $APP"
echo "Donnees CSV : $HOME/Documents/BalanceCollecteur/data balance/"
echo "Brancher la balance USB avant de lancer l'application."
