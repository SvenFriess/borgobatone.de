#!/usr/bin/env bash
set -euo pipefail

# --- PATH härten, damit signal-cli sicher gefunden wird ---
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

BOT_DIR="$HOME/Projekte/borgobatone.de"
ENV_FILE="$BOT_DIR/env_vars.sh"
VENV="$BOT_DIR/venv"
PY="$VENV/bin/python"
BOT_FILE="signal_bot_carola_gruppe_staticid_popen_llm_logging_fixed.py"
BOT_PATH="$BOT_DIR/$BOT_FILE"
LOG="$BOT_DIR/bot.log"
PID_FILE="$BOT_DIR/bot.pid"

# Env laden (nicht fatal, wenn fehlt)
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE" || true

# Sanity
command -v "$PY" >/dev/null || { echo "❌ Python im venv fehlt: $PY"; exit 1; }
[[ -f "$BOT_PATH" ]] || { echo "❌ Bot-Datei fehlt: $BOT_PATH"; exit 1; }
command -v signal-cli >/dev/null || echo "⚠️  signal-cli nicht im PATH"

# Doppelstarter verhindern (darf nie das Script killen, daher '|| true')
pkill -f 'signal_bot_.*\.py' 2>/dev/null || true
pkill -f 'org\.asamk\.signal\.Main -u \+4915755901211 .* receive' 2>/dev/null || true

# Info
echo "ℹ️  GROUP_ID=${GROUP_ID:0:6}…"
echo "🚀 Starte $BOT_FILE …"

# Start
mkdir -p "$BOT_DIR"
: > "$LOG"  # optional: Log leeren
nohup "$PY" "$BOT_PATH" >> "$LOG" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"

# Kurze Wartezeit, dann prüfen
sleep 0.7
if ps -p "$PID" >/dev/null 2>&1; then
  echo "✅ Bot gestartet, PID $PID (Log: $LOG)"
else
  echo "❌ Bot-Prozess nicht aktiv – Details aus Log:"
  tail -n 50 "$LOG" || true
  exit 1
fi