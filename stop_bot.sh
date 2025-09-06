#!/usr/bin/env bash
set -euo pipefail
BOT_DIR="$HOME/Projekte/borgobatone.de"
PID_FILE="$BOT_DIR/bot.pid"
if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE")
  if ps -p "$PID" >/dev/null 2>&1; then
    kill "$PID" 2>/dev/null || true
    sleep 0.5
    if ps -p "$PID" >/dev/null 2>&1; then
      kill -9 "$PID" 2>/dev/null || true
    fi
    echo "🛑 Bot (PID $PID) gestoppt."
  fi
  rm -f "$PID_FILE"
else
  echo "ℹ️  Kein PID-File gefunden – Bot lief wohl nicht."
fi
pkill -f 'org\.asamk\.signal\.Main -u \+4915755901211 -o json receive' 2>/dev/null || true
pkill -f 'signal-cli -u \+4915755901211 -o json receive' 2>/dev/null || true
sleep 0.2
pkill -9 -f 'org\.asamk\.signal\.Main -u \+4915755901211 -o json receive' 2>/dev/null || true
