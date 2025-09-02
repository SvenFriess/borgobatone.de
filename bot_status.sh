#!/bin/bash
# Bot-Status prüfen + Logs live verfolgen

LOGFILE="$HOME/Projekte/borgobatone.de/bot.log"

if pgrep -fl "signal_bot" >/dev/null; then
    echo "✅ Bot läuft"
    pgrep -fl "signal_bot"
    echo
    echo "📄 Logausgabe (letzte 5 Zeilen + live follow):"
    if [ -f "$LOGFILE" ]; then
        tail -n 5 -f "$LOGFILE"
    else
        echo "⚠️  Kein Logfile gefunden: $LOGFILE"
    fi
else
    echo "❌ Bot gestoppt"
fi

