#!/bin/bash
cd "$HOME/Projekte/borgobatone.de" || exit 1
[ -d venv ] && source venv/bin/activate
pkill -f "signal_bot" 2>/dev/null || true
pkill -f "org\.asamk\.signal\.Main .* receive" 2>/dev/null || true
: > bot.log
export USE_JSON=1 RECEIVE_TIMEOUT=120
nohup python -u signal_bot_carola_gruppe_STATICID_POPEN_LLM_LOGGING_DEBUG_WORKS.py >> bot.log 2>&1 &
echo $! > bot.pid
echo "✅ Bot gestartet, PID $(cat bot.pid)"
