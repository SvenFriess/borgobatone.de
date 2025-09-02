#!/bin/bash
cd "$HOME/Projekte/borgobatone.de" || exit 1
if [ -f bot.pid ] && kill -0 "$(cat bot.pid)" 2>/dev/null; then
  kill "$(cat bot.pid)" && echo "🛑 Bot (PID $(cat bot.pid)) gestoppt."
  rm -f bot.pid
else
  pkill -f "signal_bot" && echo "🛑 Bot-Prozess(e) beendet."
fi
