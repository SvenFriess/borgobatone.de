#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =======================
# Imports
# =======================
import os
import re
import json
import time
import shlex
import logging
import subprocess
import hashlib
import traceback
from pathlib import Path
from typing import Iterable, Iterator, Optional, Tuple

# =======================
# Kontext-Loader mit Hot-Reload
# =======================
# WICHTIG: CONTEXT_FILE als Path, damit .exists()/.read_text() etc. überall funktionieren
CONTEXT_FILE = Path(os.getenv(
    "CONTEXT_FILE",
    "/Users/svenfriess/Projekte/borgobatone.de/borgobatone.txt"
))

_CTX_CACHE = ""
_CTX_MTIME: Optional[float] = None

def load_context(force: bool = False) -> str:
    """Lädt die Kontextdatei mit Hot-Reload und gibt den Text zurück."""
    global _CTX_CACHE, _CTX_MTIME
    try:
        if not CONTEXT_FILE.exists():
            print(f"[CTX][WARN] Kontextdatei nicht gefunden: {CONTEXT_FILE}")
            _CTX_CACHE = ""
            _CTX_MTIME = None
            return _CTX_CACHE

        mtime = CONTEXT_FILE.stat().st_mtime
        if force or _CTX_MTIME is None or mtime != _CTX_MTIME:
            _CTX_CACHE = CONTEXT_FILE.read_text(encoding="utf-8", errors="ignore")
            _CTX_MTIME = mtime
            sha1 = hashlib.sha1(_CTX_CACHE.encode("utf-8")).hexdigest()[:8]
            print(f"[CTX] Loaded {CONTEXT_FILE} len={len(_CTX_CACHE)} sha1={sha1}")
    except Exception as e:
        print("[CTX][ERROR]", e)
        traceback.print_exc()
        _CTX_CACHE = ""
    return _CTX_CACHE

# initial laden
load_context(force=True)

def build_prompt(user_input: str) -> str:
    """Erzeugt den LLM-Prompt inkl. aktuellem (Hot-Reload) Kontext + Debug-Vorschau."""
    ctx = load_context(False)  # Hot-Reload on change
    prompt = (
        "### Borgo-Batone Kontext ###\n" + ctx +
        "\n### Ende Kontext ###\n" +
        f"User: {user_input}\nAssistant:"
    )
    preview = prompt[:300] + (f"\n...[{len(prompt)-300} chars more]" if len(prompt) > 300 else "")
    print("[PROMPT][DEBUG]\n", preview)
    return prompt

# =======================
# Konfiguration
# =======================
BOT_NUMBER = os.environ.get("BOT_NUMBER", "+4915755901211").strip()
SIGNAL_CLI = os.environ.get("SIGNAL_CLI", "signal-cli").strip()
GROUP_ID_STATIC = os.environ.get("GROUP_ID", "").strip()        # optional: feste Zielgruppe (Base64-ID)

# RECEIVE_TIMEOUT aus ENV lesen, mit Sicherheits-Defaults
timeout_raw = os.environ.get("RECEIVE_TIMEOUT", "30")
try:
    RECEIVE_TIMEOUT = int(timeout_raw)
except ValueError:
    print(f"⚠️ RECEIVE_TIMEOUT ungültig ('{timeout_raw}'), automatisch auf 30 gesetzt")
    RECEIVE_TIMEOUT = 30

if RECEIVE_TIMEOUT < 10 or RECEIVE_TIMEOUT > 600:
    print(f"⚠️ RECEIVE_TIMEOUT außerhalb des erlaubten Bereichs (10–600): {RECEIVE_TIMEOUT}, automatisch auf 30 gesetzt")
    RECEIVE_TIMEOUT = 30

USE_JSON = os.environ.get("USE_JSON", "1") == "1"                # JSON-Receiver standardmäßig an

BASE_DIR = Path(os.environ.get("BOT_BASE", str(Path.home() / "Projekte" / "borgobatone.de")))
LOG_PATH = BASE_DIR / "bot.log"

# =======================
# Logging nur in Datei (kein Doppel-Stream)
# =======================
for h in logging.root.handlers[:]:
    logging.root.removeHandler(h)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8")],
)

# =======================
# Startkonfiguration ins Log schreiben
# =======================
logging.info("⚙️ Konfiguration:")
logging.info(f"   BOT_NUMBER      = {BOT_NUMBER}")
logging.info(f"   GROUP_ID_STATIC = {GROUP_ID_STATIC or '(keine)'}")
logging.info(f"   CONTEXT_FILE    = {CONTEXT_FILE}")
logging.info(f"   RECEIVE_TIMEOUT = {RECEIVE_TIMEOUT} Sekunden")
logging.info(f"   USE_JSON        = {USE_JSON}")

# =======================
# LLM-Integration (optional)
# =======================
def llm_answer(question: str, context: str) -> str:
    """
    Versucht, ein lokales LLM zu nutzen (falls Modul vorhanden).
    Fallback: sehr einfacher kontextbasierter Antwortgenerator.
    Erwartetes Interface (optional):
        from local_llm_interface import generate_answer
        generate_answer(user_question: str, context: str) -> str
    """
    try:
        from local_llm_interface import generate_answer  # type: ignore
        ans = generate_answer(question, context or "")
        if isinstance(ans, str) and ans.strip():
            return ans.strip()
    except Exception as e:
        logging.warning(f"LLM nicht verfügbar oder Fehler: {e}")

    # Simpler kontextueller Fallback (greift Stichworte aus dem Kontext auf)
    if not context:
        return "ℹ️ Ich habe dazu gerade keinen lokalen Kontext. Formuliere deine Frage bitte etwas konkreter."

    # naive „Best Effort“-Suche einiger Sätze aus dem Kontext
    q = question.strip().lower()
    lines = [ln.strip() for ln in context.splitlines() if ln.strip()]
    hit_lines = [ln for ln in lines if any(tok in ln.lower() for tok in q.split() if len(tok) > 2)]
    if not hit_lines:
        return "🔎 Ich habe in meinem lokalen Kontext nichts Passendes gefunden. Frag gerne anders oder konkreter."
    snippet = "\n".join(hit_lines[:6])
    return f"📚 Aus dem lokalen Kontext:\n{snippet}"

# =======================
# Utilities / Parsing
# =======================
CMD_TRIGGER = re.compile(r"^\s*!bot\b", re.IGNORECASE)
WHITESPACE = re.compile(r"\s+")

def normalize_text(s: str) -> str:
    return WHITESPACE.sub(" ", (s or "")).strip()

def parse_command(msg: str) -> Tuple[str, str]:
    """
    Gibt (cmd, rest) zurück. Beispiel:
      '!bot einkaufen milch' -> ('einkaufen', 'milch')
      '!Bot HALLO' -> ('hallo', '')
    """
    if not CMD_TRIGGER.search(msg or ""):
        return "", ""
    text = CMD_TRIGGER.sub("", msg, count=1)  # '!bot' entfernen (egal welche Groß/Kleinschreibung)
    text = normalize_text(text)
    if not text:
        return "help", ""
    parts = text.split(" ", 1)
    cmd = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""
    # einfache Aliase
    if cmd == "einkauf":
        cmd = "einkaufen"
    return cmd, rest

def build_answer(cmd: str, rest: str) -> str:
    # 1) Harte, sofortige Antworten (synchron, ohne LLM)
    if cmd in ("hallo", "hello", "hi"):
        return "👋 Hallo! Ich bin da."
    if cmd in ("status",):
        return "✅ Bot läuft. Sende `!bot hallo`, `!bot einkaufen`, oder frage frei mit `!bot <Frage>`."
    if cmd in ("einkauf", "einkaufen"):
        return (
            "🛒 **Einkaufen – kurz & knackig**\n"
            "- **S. Martino in Freddana:** Carrefour & Bäckerei.\n"
            "- Unten an der Hauptstraße: „Alimentari Pini“ (Brot, Milch, Obst/Gemüse).\n"
        )
    if cmd in ("pizza",):
        return "🍕 Pizza-Info folgt vor Ort – frag gern nach dem Pizzaofen-Setup."

    # 2) „help“ / unbekannt → kurzes, nicht-aufgeblähtes Fallback
    if cmd in ("help", "hilfe", "?", ""):
        return ("ℹ️ **Borgo-Bot Befehle:** `!bot hallo`, `!bot einkaufen`, `!bot status`.\n"
                "Frag sonst frei mit `!bot <Frage>` – ich nutze dann lokalen Kontext (`borgobatone.txt`).")

    # 3) Freier Prompt → LLM (mit Hot-Reload-Kontext)
    question = normalize_text(f"{cmd} {rest}".strip())
    if not question:
        return ("ℹ️ **Unklare Eingabe.** Beispiele: `!bot hallo`, `!bot einkaufen`, "
                "`!bot Wo kann ich Brot kaufen?`")
    return llm_answer(question, load_context(False))  # <— Hot-Reload hier genutzt

# =======================
# signal-cli Receive/Send
# =======================
def run_receive() -> Iterator[Tuple[str, str]]:
    """
    Iterator liefert (group_id, message_text) für eingehende Nachrichten.
    Nutzt JSON-Ausgabe, um Quittungen/Lesebestätigungen sauber zu ignorieren.
    """
    base_cmd = [SIGNAL_CLI, "-u", BOT_NUMBER]
    if USE_JSON:
        cmd = base_cmd + ["-o", "json", "receive", "-t", str(RECEIVE_TIMEOUT)]
    else:
        cmd = base_cmd + ["receive", "-t", str(RECEIVE_TIMEOUT)]

    logging.debug("START RECEIVE: " + " ".join(shlex.quote(c) for c in cmd))

    with subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    ) as proc:
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.strip()
            if not line:
                continue

            if USE_JSON:
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                env = obj.get("envelope") or {}
                dm = env.get("dataMessage") or {}
                if not dm:
                    continue
                text = dm.get("message") or ""
                gi = dm.get("groupInfo") or {}
                gid = gi.get("groupId")
                if not (gid and text):
                    continue
                yield gid, text
            else:
                if "dataMessage" not in line:
                    continue
                continue

        rc = proc.poll()
        if rc == 0:
            logging.warning("receive beendet (rc=0) – Neustart in 1s …")
        else:
            logging.error(f"receive beendet (rc={rc}) – Neustart in 3s …")

def send_group_message(group_id: str, text: str) -> None:
    text = text or ""
    segments = []
    MAX_LEN = 1400
    while text:
        segments.append(text[:MAX_LEN])
        text = text[MAX_LEN:]

    for seg in segments:
        cmd = [SIGNAL_CLI, "-u", BOT_NUMBER, "send", "-g", group_id, "-m", seg]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Sende-Fehler: {e.stderr or e.stdout}")

# =======================
# Hauptloop
# =======================
def main() -> None:
    logging.info("🚀 Bot gestartet")
    logging.info("🤖 Bot läuft und lauscht ...")

    if GROUP_ID_STATIC:
        logging.info(f"🎯 Feste GROUP_ID aktiv: {GROUP_ID_STATIC[:8]}…")
    else:
        logging.info("🎯 Keine feste GROUP_ID gesetzt – antworte in die eingehende Gruppe")

    while True:
        try:
            for group_id, message in run_receive():
                if GROUP_ID_STATIC and group_id != GROUP_ID_STATIC:
                    continue

                msg_norm = normalize_text(message)
                if not CMD_TRIGGER.search(msg_norm):
                    continue

                cmd, rest = parse_command(msg_norm)
                logging.debug(f"📥 Eingegangen: cmd='{cmd}' rest='{rest}'")

                answer = build_answer(cmd, rest)
                logging.debug(f"🧠 Antwort vorbereitet ({len(answer)} Zeichen)")

                target_gid = GROUP_ID_STATIC or group_id
                send_group_message(target_gid, answer)
                logging.debug("📤 Antwort gesendet")
        except Exception as e:
            logging.exception(f"Hauptloop-Fehler: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()