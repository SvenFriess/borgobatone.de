#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
signal_bot_carola_gruppe_staticid_popen_llm_logging_fixed.py
Vollversion mit:
- ENV-Timeout (RECV_TIMEOUT, default 300s) für signal-cli receive
- SEND_TIMEOUT=30s, sanfter Send-Retry (park receive -> retry -> restart)
- Rotating Logging in ~/Projekte/borgobatone.de/bot.log
- Dedupe (TTL 10 min) gegen doppelte Verarbeitung
- FIXED_RESPONSES und LLM-Fallback (local_llm_interface.generate)
- Antwort nur in der Zielgruppe (GROUP_ID), falls gesetzt
"""

import os
import sys
import time
import json
import signal as sig
import subprocess
import threading
import logging
from logging.handlers import RotatingFileHandler
from collections import OrderedDict
from typing import Optional, Tuple

# =========================
# ---- Konfiguration  -----
# =========================
BOT_DIR = os.path.expanduser("~/Projekte/borgobatone.de")
LOG_FILE = os.path.join(BOT_DIR, "bot.log")

SIGNAL_NUMBER = os.environ.get("SIGNAL_NUMBER", "").strip()
GROUP_ID      = os.environ.get("GROUP_ID", "").strip()  # Base64-ID der Zielgruppe
USE_JSON      = True

# Timeouts (ENV-steuerbar)
RECV_TIMEOUT  = int(os.environ.get("RECV_TIMEOUT", "300"))  # Sekunden
SEND_TIMEOUT  = int(os.environ.get("SEND_TIMEOUT", "30"))   # Sekunden

# LLM (optional)
MODEL_NAME   = os.environ.get("LLM_MODEL", "mistral")
MAX_TOKENS   = int(os.environ.get("LLM_MAX_TOKENS", "512"))
TEMPERATURE  = float(os.environ.get("LLM_TEMPERATURE", "0.4"))
LLM_TIMEOUT  = int(os.environ.get("LLM_TIMEOUT", "45"))

# Feste Kurzantworten
FIXED_RESPONSES = {
    "ping":  "✅ Bot läuft.",
    "hallo": "👋 Hallo! Ich bin da.",
    "hello": "👋 Hello! I’m here.",
    "!help": "Befehle: ping, hallo, hello — sonst antworte ich kurz via LLM.",
}

# =========================
# ---- Logging ------------
# =========================
os.makedirs(BOT_DIR, exist_ok=True)
logger = logging.getLogger("borgo-bot")
logger.setLevel(logging.INFO)
if not logger.handlers:
    rh = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    rh.setFormatter(fmt)
    logger.addHandler(rh)

# =========================
# ---- Dedupe -------------
# =========================
DEDUP_TTL_S = 600     # 10 Minuten
DEDUP_MAX   = 2000
_seen = OrderedDict()

def make_msg_key(env: dict, dm: dict) -> str:
    ts  = env.get('serverReceiveTimestamp') or env.get('timestamp') or dm.get('timestamp') or 0
    src = env.get('sourceUuid') or env.get('source') or ''
    msg = (dm.get('message') or '').strip()
    return f"{ts}|{src}|{hash(msg)}"

def seen_recent(key: str) -> bool:
    now = time.time()
    # abgelaufene vom Anfang entfernen
    for k, (t, _) in list(_seen.items()):
        if now - t > DEDUP_TTL_S:
            _seen.pop(k, None)
        else:
            break
    if key in _seen:
        return True
    _seen[key] = (now, 1)
    # Begrenzen
    if len(_seen) > DEDUP_MAX:
        try:
            _seen.popitem(last=False)
        except Exception:
            pass
    return False

# =========================
# ---- LLM ----------------
# =========================
class LLMError(Exception):
    pass

def llm_generate(prompt: str) -> str:
    start = time.time()
    try:
        from local_llm_interface import generate
        out = generate(
            prompt,
            model=MODEL_NAME,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            timeout_s=LLM_TIMEOUT,
        )
        dur = time.time() - start
        logger.info(f"[LLM] Modell={MODEL_NAME}, Dauer={dur:.2f}s, Prompt-Länge={len(prompt)}")
        return out
    except ImportError:
        raise LLMError("local_llm_interface.py nicht gefunden.")
    except Exception as e:
        raise LLMError(str(e))

# =========================
# ---- signal-cli ---------
# =========================
_recv_proc: Optional[subprocess.Popen] = None
_recv_lock = threading.Lock()

def _receive_cmd():
    return ["signal-cli", "-u", SIGNAL_NUMBER, "-o", "json", "receive", "-t", str(RECV_TIMEOUT)]

def _start_receive() -> subprocess.Popen:
    global _recv_proc
    with _recv_lock:
        if _recv_proc and _recv_proc.poll() is None:
            return _recv_proc
        cmd = _receive_cmd()
        logger.info(f"[RECV] starte: {' '.join(cmd)}")
        _recv_proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
        )
        threading.Thread(target=_drain_stderr, args=(_recv_proc,), daemon=True).start()
        return _recv_proc

def _stop_receive(hard: bool = False):
    global _recv_proc
    with _recv_lock:
        if not _recv_proc:
            return
        if _recv_proc.poll() is None:
            try:
                if hard:
                    _recv_proc.kill()
                else:
                    _recv_proc.terminate()
                _recv_proc.wait(timeout=1.2)
            except Exception:
                try:
                    _recv_proc.kill()
                    _recv_proc.wait(timeout=0.8)
                except Exception:
                    pass
        _recv_proc = None

def _drain_stderr(proc: subprocess.Popen):
    try:
        for line in proc.stderr:
            line = (line or "").strip()
            if not line:
                continue
            if "Config file is in use by another instance" in line:
                logger.info(f"[RECV] stderr={line}")  # normal bei Lockwechseln
            elif "Connection closed unexpectedly" in line:
                logger.warning(f"[RECV] stderr={line}")
            # sonst stiller – Logflut vermeiden
    except Exception:
        pass

def send_group_msg(group_id: str, text: str) -> bool:
    """
    Stabiler Send: Bei Timeout receive sanft pausieren und einmal retry.
    """
    if not group_id:
        logger.error("[SEND] Kein group_id angegeben – Abbruch.")
        return False
    cmd = ["signal-cli", "-u", SIGNAL_NUMBER, "send", "-g", group_id, "-m", text]
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=SEND_TIMEOUT)
        if proc.returncode == 0:
            logger.info("[SEND] OK")
            return True
        logger.warning(f"[SEND] Fehler rc={proc.returncode}, stderr={proc.stderr.strip()}")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("[SEND] Timeout – versuche Reset + Retry …")
        _stop_receive(hard=False)
        time.sleep(0.6)
        try:
            proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=SEND_TIMEOUT)
            if proc.returncode == 0:
                logger.info("[SEND] OK nach Retry")
                return True
            logger.error(f"[SEND] Retry rc={proc.returncode}, stderr={proc.stderr.strip()}")
            return False
        finally:
            try:
                _start_receive()
            except Exception:
                pass

# =========================
# ---- Parsing/Handling ---
# =========================
def parse_text_and_group(obj: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Erwartet JSON-Linien von 'signal-cli -o json receive'.
    Gibt (group_id, text, dedupe_key) zurück.
    """
    try:
        env = obj.get("envelope") or obj
        dm  = env.get("dataMessage") if isinstance(env, dict) else None
        if not dm:
            return None, None, None
        group_info = dm.get("groupInfo") or {}
        group_id = group_info.get("groupId")  # base64
        text = dm.get("message")
        key  = make_msg_key(env, dm)
        return group_id, text, key
    except Exception:
        return None, None, None

def handle_text(text: str) -> str:
    if not text:
        return ""
    low = text.strip().lower()
    if low in FIXED_RESPONSES:
        return FIXED_RESPONSES[low]

    # LLM-Fallback kurz & hilfreich auf Deutsch
    try:
        prompt = f"Beantworte kurz und hilfreich auf Deutsch:\n\n{text}\n"
        return llm_generate(prompt)
    except Exception as e:
        logger.error(f"[LLM] Fehler: {e}")
        return "⚠️ LLM gerade nicht erreichbar. Versuch es später nochmal."

# =========================
# ---- Main ---------------
# =========================
def main():
    if not SIGNAL_NUMBER:
        logger.error("[BOOT] SIGNAL_NUMBER fehlt – Abbruch.")
        sys.exit(1)
    if not GROUP_ID:
        logger.warning("[BOOT] GROUP_ID ist leer. Der Bot kann sonst nicht in die Gruppe antworten.")

    logger.info("[BOOT] Borgo-Bot TEST startet (Popen/receive, Dedup aktiv)…")
    logger.info(f"[CFG] number={SIGNAL_NUMBER} group={(GROUP_ID[:6]+'…') if GROUP_ID else '—'} json={USE_JSON} t={RECV_TIMEOUT}s")

    proc = _start_receive()

    def _shutdown(*_):
        logger.info("[EXIT] SIGINT/SIGTERM – tschüss ✌️")
        _stop_receive(hard=True)
        sys.exit(0)

    sig.signal(sig.SIGINT, _shutdown)
    sig.signal(sig.SIGTERM, _shutdown)

    while True:
        # Falls receive beendet wurde: neu starten
        if proc.poll() is not None:
            rc = proc.returncode
            logger.warning(f"[RECV] beendet (rc={rc}).")
            time.sleep(0.3)
            proc = _start_receive()

        line = proc.stdout.readline() if proc.stdout else ""
        if not line:
            time.sleep(0.03)
            continue

        line = line.strip()
        if not line:
            continue

        if not USE_JSON:
            # (hier immer JSON)
            continue

        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        group_id, text, key = parse_text_and_group(obj)
        if not text:
            continue
        # Nur Zielgruppe bedienen (falls GROUP_ID gesetzt)
        if GROUP_ID and group_id and group_id != GROUP_ID:
            continue
        # Dedupe
        if key and seen_recent(key):
            logger.info("[DEDUP] übersprungen.")
            continue

        reply = handle_text(text)
        if not reply:
            continue

        ok = send_group_msg(GROUP_ID or group_id or "", reply)
        if not ok:
            logger.error("[SEND] Nachricht konnte nicht gesendet werden.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("[EXIT] KeyboardInterrupt – tschüss ✌️")
    except Exception as e:
        logger.exception(f"[FATAL] {e}")
        raise