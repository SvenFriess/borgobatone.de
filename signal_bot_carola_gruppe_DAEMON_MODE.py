import json
import logging
import subprocess
import time
from datetime import datetime
from local_llm_interface import generate_response_with_llm

# === Konfiguration ===
BOT_NUMBER = "+4915755901211"
GROUP_ID = "21oiqcpO37/ScyKFhmctf/45MQ5QYdN2h/VQp9WMKCM="
TRIGGER_KEYWORDS = ["!Bot", "!bot", "bot:", "@bot"]
RESPONSE_PREFIX = "🤖: "

# === Logging ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot_daemon_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === Funktion: Nachricht senden ===
def sende_nachricht(text):
    try:
        subprocess.run([
            "signal-cli", "-u", BOT_NUMBER, "send",
            "-g", GROUP_ID,
            "-m", RESPONSE_PREFIX + text
        ], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Fehler beim Senden: {e}")

# === Funktion: Ereignisse aus daemon lesen ===
def empfange_nachrichten():
    cmd = ["signal-cli", "-u", BOT_NUMBER, "daemon", "--json"]
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True) as proc:
        for line in proc.stdout:
            try:
                event = json.loads(line.strip())
                yield event
            except json.JSONDecodeError:
                continue

# === Hauptlogik ===
def verarbeite_event(event):
    envelope = event.get("envelope", {})
    message = envelope.get("dataMessage", {})
    group_info = message.get("groupInfo", {})
    text = message.get("message")

    if not text:
        return

    current_group = group_info.get("groupId")
    if current_group != GROUP_ID:
        return

    if not any(trigger in text for trigger in TRIGGER_KEYWORDS):
        return

    logger.info(f"📩 Trigger erkannt: {text!r}")
    antwort = generate_response_with_llm(text)
    sende_nachricht(antwort)

# === Main Loop ===
if __name__ == "__main__":
    logger.info("🚀 Bot im DAEMON-Modus gestartet")
    try:
        for event in empfange_nachrichten():
            verarbeite_event(event)
    except KeyboardInterrupt:
        logger.info("⛔ Bot manuell beendet")
    except Exception as e:
        logger.exception(f"💥 Unerwarteter Fehler: {e}")