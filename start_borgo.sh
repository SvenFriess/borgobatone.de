#!/bin/bash

# === Konfiguration ===
PROJEKT_DIR="/Users/svenfriess/Projekte/borgobatone.de"
VENV="$PROJEKT_DIR/venv"
FLASK_APP="app_modifiziert_mistral_DEBUG.py"
SIGNAL_BOT="signal_bot.py"
LOGFILE="$PROJEKT_DIR/log_borgo.log"

# === ollama serve starten (nur wenn nicht läuft) ===
if ! pgrep -f "ollama serve" > /dev/null; then
    echo "[INFO] $(date) - Starte ollama serve ..." >> "$LOGFILE"
    ollama serve >> "$LOGFILE" 2>&1 &
    sleep 3
else
    echo "[INFO] $(date) - ollama serve läuft bereits" >> "$LOGFILE"
fi

# === virtuelle Umgebung aktivieren ===
source "$VENV/bin/activate"

# === Flask-App starten ===
echo "[INFO] $(date) - Starte Flask-App ..." >> "$LOGFILE"
python "$PROJEKT_DIR/$FLASK_APP" >> "$LOGFILE" 2>&1 &

# === Signal-Bot starten ===
echo "[INFO] $(date) - Starte Signal-Bot ..." >> "$LOGFILE"
python "$PROJEKT_DIR/$SIGNAL_BOT" >> "$LOGFILE" 2>&1 &

# === ngrok starten ===
echo "[INFO] $(date) - Starte ngrok mit reservierter Domain ..." >> "$LOGFILE"
ngrok http --domain=borgobatone.ngrok.app 5200 >> "$LOGFILE" 2>&1 &