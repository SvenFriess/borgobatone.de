# config.py – zentrale Konfiguration für Borgo-Bot

# Telefonnummer, unter der signal-cli für den Bot registriert ist
SIGNAL_PHONE_NUMBER = "+4915755901211"

# Erlaubte Gruppen (Signal Group IDs) – nur hier reagiert der Bot
GROUP_ALLOWLIST = {
    "21oiqcpO37/ScyKFhmctf/45MQ5QYdN2h/VQp9WMKCM="  # Borgo-Bot
}

# Trigger-Terme für einfache Bot-Kommandos
TRIGGER_TERMS = ["!bot", "!hilfe", "!help", "!status"]

# Regulärer Ausdruck für Trigger-Erkennung
import re
BOT_KEYWORD_PATTERN = re.compile(r"(?:^|\s)!(?:bot|hilfe|help|status)\b", re.IGNORECASE)

# Pfad zu signal-cli
SIGNAL_CLI = "signal-cli"

# Timeout für receive-Aufrufe (Sekunden)
RECEIVE_TIMEOUT = 30

# Loglevel
LOGLEVEL = "INFO"

# Pfad zur Borgo-Batone-Kontextdatei
CONTEXT_PATH = "/Users/svenfriess/Projekte/borgobatone.de/borgobatone.txt"

# Maximal gelesene Zeichen aus dem Kontextfile
CONTEXT_CHARS = 6000

# Ollama-Modellname
LLM_MODEL = "mistral:instruct"