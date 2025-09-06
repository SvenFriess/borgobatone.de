#!/usr/bin/env bash
set -euo pipefail

BOT_DIR="$HOME/Projekte/borgobatone.de"
PID_FILE="$BOT_DIR/bot.pid"
LOG="$BOT_DIR/bot.log"

echo "=== Bot Status ==="
if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE")
  if ps -p "$PID" >/dev/null 2>&1; then
    echo "✅ Bot läuft (PID $PID)"
  else
    echo "❌ Bot-PID-File vorhanden, aber Prozess nicht aktiv"
  fi
else
  echo "❌ Kein Bot-PID-File"
fi

echo
echo "=== signal-cli receive ==="
found=""
for i in {1..6}; do  # bis zu 3s warten
  if pgrep -af "signal-cli.* -u \+4915755901211 .* receive" >/dev/null \
  || pgrep -af "org\.asamk\.signal\.Main .* -u \+4915755901211 .* receive" >/dev/null; then
    pgrep -af "signal-cli.* -u \+4915755901211 .* receive" || true
    pgrep -af "org\.asamk\.signal\.Main .* -u \+4915755901211 .* receive" || true
    found="yes"
    break
  fi
  sleep 0.5
done
[[ -z "$found" ]] && echo "ℹ️  kein receive-Prozess sichtbar (läuft evtl. gerade neu an)"

if [[ -f "$LOG" ]]; then
  last_recv_start=$(grep "\[RECV\] starte:" "$LOG" | tail -n 1 || true)
  if [[ -n "${last_recv_start:-}" ]]; then
    echo
    echo "Letzter receive-Start laut Log:"
    echo "$last_recv_start"
  fi
fi
