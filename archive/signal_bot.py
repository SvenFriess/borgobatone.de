import subprocess
import time
import logging
import os
import re
from logging.handlers import RotatingFileHandler
from datetime import datetime

import config  # central settings

# === Logger ===
def setup_logger():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "signal_bot.log")

    formatter_file = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    formatter_console = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

    try:
        import colorlog
        formatter_console = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s [%(levelname)s]%(reset)s %(message)s",
            datefmt="%H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
    except Exception:
        pass

    console = logging.StreamHandler()
    console.setFormatter(formatter_console)

    file_handler = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter_file)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, config.LOGLEVEL.upper(), logging.INFO))
    root.addHandler(console)
    root.addHandler(file_handler)

setup_logger()
logger = logging.getLogger(__name__)

SIGNAL_PHONE_NUMBER = config.SIGNAL_PHONE_NUMBER
GROUP_ALLOWLIST = set(config.GROUP_ALLOWLIST)
KEYWORD_PATTERN = config.BOT_KEYWORD_PATTERN
SIGNAL_CLI = config.SIGNAL_CLI

# --- Helpers ---
def extract_group_id(line: str) -> str | None:
    # Try multiple patterns commonly seen in signal-cli receive output
    # e.g., "Group ID: ABC..." or "groupId: ABC..." or "groupId=ABC..."
    m = re.search(r"(?:groupId|Group ID)[:=]\s*([A-Za-z0-9+/=]{10,})", line)
    return m.group(1) if m else None

def extract_body(line: str) -> str | None:
    # e.g., "Body: text..." or "Message: text..."
    m = re.search(r"(?:Body|Message)[:]\s*(.*)$", line)
    return m.group(1).strip() if m else None

def send_group_message(group_id: str, text: str) -> None:
    logger.info(f"📤 Antwort an Gruppe {group_id[:6]}…: {text}")
    try:
        subprocess.run([SIGNAL_CLI, "-u", SIGNAL_PHONE_NUMBER, "send", "-g", group_id, "-m", text], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Senden fehlgeschlagen: {e}")

def generate_response(text: str) -> str:
    # Strip first keyword occurrence for echo-style demo
    cleaned = KEYWORD_PATTERN.sub("", text, count=1).strip()
    if not cleaned:
        cleaned = "pong"
    return f"🧠 {cleaned}"

def process_line(line: str) -> None:
    group_id = extract_group_id(line)
    if not group_id:
        return
    if GROUP_ALLOWLIST and group_id not in GROUP_ALLOWLIST:
        logger.debug(f"⛔️ Gruppe nicht erlaubt: {group_id}")
        return
    body = extract_body(line)
    if not body:
        return
    if not KEYWORD_PATTERN.search(body):
        return
    logger.info(f"✅ Trigger erkannt in Gruppe {group_id[:6]}…: {body}")
    resp = generate_response(body)
    send_group_message(group_id, resp)

def receive_messages() -> None:
    logger.info("🤖 Signal-Bot läuft und lauscht auf Gruppennachrichten ...")
    cmd = [SIGNAL_CLI, "-u", SIGNAL_PHONE_NUMBER, "receive", "-t", str(config.RECEIVE_TIMEOUT)]
    while True:
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # stream lines until timeout; signal-cli exits after -t seconds idle
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                logger.debug(f"📥 {line}")
                process_line(line)
            # drain stderr for diagnostics
            err = proc.stderr.read().strip()
            if err:
                logger.debug(f"stderr: {err}")
        except KeyboardInterrupt:
            logger.warning("⛔️ Bot wurde manuell beendet.")
            break
        except Exception as e:
            logger.exception(f"❌ receive loop error: {e}")
            time.sleep(2)  # backoff

if __name__ == "__main__":
    receive_messages()
