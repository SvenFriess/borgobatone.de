#!/bin/zsh
CONFIG="$HOME/.config/signal-cli-borgo-bot-2"
NUMBER="+491744519652"
open "https://signalcaptchas.org/registration/generate.html"
echo "Löse das Captcha, dann: Rechtsklick auf 'Open Signal' → Link-Adresse kopieren."
LAST=""
while true; do
  CLIP="$(pbpaste 2>/dev/null | tr -d '\r')"
  [[ -z "$CLIP" || "$CLIP" == "$LAST" ]] && { sleep 0.2; continue; }
  LAST="$CLIP"
  [[ "$CLIP" == signalcaptcha://signal-hcaptcha*registration.P1_* ]] || continue
  TOKEN="${CLIP##*registration.P1_}"
  LEN=${#TOKEN}
  [[ $LEN -lt 200 ]] && { echo "Token zu kurz ($LEN). Nochmal kopieren."; continue; }
  echo "Registriere … (Token-Länge $LEN)"
  signal-cli --config "$CONFIG" -u "$NUMBER" register --captcha "$TOKEN" && {
    echo "✅ Register OK. Jetzt verify mit SMS-Code:"
    echo "signal-cli --config \"$CONFIG\" -u \"$NUMBER\" verify 123-456"
    exit 0
  }
  echo "❌ Register fehlgeschlagen (vermutlich Token zu alt). Seite neu laden, Captcha erneut lösen."
done
