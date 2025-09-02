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
from typing import Iterator, Optional, Tuple

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
# Kontext-Betriebsmodus & Helfer
# =======================
# CTX_MODE=strict|assist  (default: assist)
CTX_MODE = os.getenv("CTX_MODE", "assist").strip().lower()
if CTX_MODE not in ("strict", "assist"):
    CTX_MODE = "assist"

def ctx_meta() -> dict:
    """Metadaten zum aktuell geladenen Kontext (für !ctx-info)."""
    try:
        mtime = CONTEXT_FILE.stat().st_mtime if CONTEXT_FILE.exists() else None
    except Exception:
        mtime = None
    from datetime import datetime
    return {
        "path": str(CONTEXT_FILE),
        "len": len(_CTX_CACHE or ""),
        "sha1": hashlib.sha1((_CTX_CACHE or "").encode("utf-8")).hexdigest()[:8] if _CTX_CACHE else "-",
        "mtime": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S") if mtime else "-",
        "mode": CTX_MODE,
    }

def ctx_quick_hits(question: str, context: str) -> int:
    """
    Sehr einfache Heuristik: zähle, wie viele >2 Zeichen lange Tokens der Frage im Kontext vorkommen.
    Dient nur als 'Guardrail' für CTX_MODE=strict.
    """
    q = (question or "").lower()
    if not q or not context:
        return 0
    tokens = [t for t in re.split(r"[^\wäöüÄÖÜß]+", q) if len(t) > 2]
    if not tokens:
        return 0
    ctx_low = context.lower()
    return sum(1 for t in tokens if t in ctx_low)

# =======================
# Konfiguration
# =======================
BOT_NUMBER = os.environ.get("BOT_NUMBER", "+4915755901211").strip()
SIGNAL_CLI = os.environ.get("SIGNAL_CLI", "signal-cli").strip()
GROUP_ID_STATIC = os.environ.get("GROUP_ID", "").strip()        # optional: feste Zielgruppe (Base64-ID)

# RECEIVE_TIMEOUT aus ENV lesen, mit Sicherheits-Defaults & Warnungen
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
logging.info(f"   CTX_MODE        = {CTX_MODE}")
logging.info(f"   RECEIVE_TIMEOUT = {RECEIVE_TIMEOUT} Sekunden")
logging.info(f"   USE_JSON        = {USE_JSON}")

# =======================
# LLM-Integration (assist/strict + Fallback)
# =======================
def llm_answer(question: str, context: str) -> str:
    """
    LLM-Aufruf in zwei Modi:
      - strict: nur aus Kontext antworten; wenn keine sinnvollen Treffer → kurzer Hinweis
      - assist: Kontext als Quelle/Leitplanke nutzen, aber frei antworten erlaubt
    Fallback bleibt erhalten, falls kein LLM verfügbar ist.
    """
    # Guardrail bei strict
    if CTX_MODE == "strict":
        hits = ctx_quick_hits(question, context)
        if hits == 0:
            return "🔒 Im lokalen Kontext finde ich dazu nichts. Formuliere anders oder frage etwas, das im Borgo-Kontext steht."

    # Einheitlicher Prompt für generate_answer (falls vorhanden)
    system_rules = (
        "Du bist der Borgo-Batone-Hausbot. Antworte präzise und knapp.\n"
        "Zitiere und nutze ausschließlich Informationen aus dem bereitgestellten Kontext.\n"
        "Wenn etwas nicht im Kontext steht, sage klar 'Nicht im Kontext' und erfinde nichts.\n"
    )
    if CTX_MODE == "assist":
        system_rules = (
            "Du bist der Borgo-Batone-Hausbot. Antworte präzise und knapp.\n"
            "Nutze den Kontext zuerst; wenn etwas nicht im Kontext steht, darfst du vorsichtig ergänzen,\n"
            "ohne zu halluzinieren. Markiere Ergänzungen deutlich als 'Außerhalb des Kontexts'.\n"
        )

    prompt = (
        f"### Regeln\n{system_rules}\n\n"
        f"### Kontext (borgobatone.txt)\n{context}\n\n"
        f"### Frage\n{question}\n\n"
        f"### Antwort (kurz, deutsch):"
    )

    try:
        # Optionales lokales Interface
        from local_llm_interface import generate_answer  # type: ignore
        # unterstütze flexible Signaturen: (question, context) ODER **kwargs
        try:
            ans = generate_answer(question=question, context=context, full_prompt=prompt)  # bevorzugt
        except TypeError:
            ans = generate_answer(question, context)  # fallback signatur
        if isinstance(ans, str) and ans.strip():
            return ans.strip()
    except Exception as e:
        logging.info(f"LLM nicht verfügbar oder Fehler – nutze Fallback: {e}")

    # Fallback: einfacher Kontextschnipsel (wie bisher)
    if not context:
        return "ℹ️ Ich habe dazu gerade keinen lokalen Kontext. Formuliere deine Frage bitte etwas konkreter."

    q = question.strip().lower()
    lines = [ln.strip() for ln in context.splitlines() if ln.strip()]
    hit_lines = [ln for ln in lines if any(tok in ln.lower() for tok in q.split() if len(tok) > 2)]
    if not hit_lines:
        if CTX_MODE == "strict":
            return "🔒 Nicht im Kontext."
        return "🔎 Ich habe im lokalen Kontext nichts Passendes gefunden. Frag gerne anders oder konkreter."
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

# =======================
# Fixe Kommandos (inkl. Kontext-Tools)
# =======================
def command_ctx_info() -> str:
    m = ctx_meta()
    return (f"🧾 Kontextinfo\n"
            f"- Datei: {m['path']}\n"
            f"- Länge: {m['len']} Zeichen\n"
            f"- SHA1:  {m['sha1']}\n"
            f"- mtime: {m['mtime']}\n"
            f"- Modus: {m['mode']}\n")

def command_ctx_reload() -> str:
    load_context(force=True)
    m = ctx_meta()
    return f"🔁 Kontext neu geladen (len={m['len']}, sha1={m['sha1']})."


# === Fixe Antworten (ohne LLM) ===
# Inhalte mit TODO bitte durch echte Daten aus borgobatone.txt/Benvenuti ergänzen.
FIXED_RESPONSES: dict[str, str] = {
    # 👋 Begrüßung & Status
    "ping": "✅ Bot läuft.",
    "hallo": "👋 Hallo! Ich bin da.",
    "hello": "👋 Hallo! Ich bin da.",
    "hi": "👋 Hallo! Ich bin da.",
    "status": "✅ Bot läuft. Sende `!bot hilfe` für eine Übersicht.",

    # 🏠 Haus & Aufenthalt
    "adresse": "🏠 **Adresse:** TODO: Straße, Hausnummer, Ort, Postleitzahl.",
    "checkliste": (
        "📋 **Abreise-Checkliste**\n"
        "- Fenster schließen\n"
        "- Müll entsorgen\n"
        "- Kühlschrank leeren\n"
        "- Schlüssel zurücklegen"
    ),
    "haustiere": "🐾 **Haustiere** – TODO: Regeln für Hunde/Katzen im Haus & Garten.",
    "haustech": (
        "🔌 **Haustechnik**\n"
        "- Waschmaschine: TODO\n"
        "- Geschirrspüler: TODO\n"
        "- Heizung/Warmwasser: TODO"
    ),
    "grill": "🍖 **Grill/Pizzaofen** – TODO: Bedienhinweise & Reinigung.",

    # 🕑 Zeiten & Regeln
    "anreise": "🕑 **Check-in** – TODO: ab xx Uhr.",
    "abreise": "🕛 **Check-out** – TODO: bis xx Uhr.",
    "ruhezeiten": "🤫 **Ruhezeiten** – TODO: z. B. 22–7 Uhr draußen leise sein.",
    "müll": (
        "🗑️ **Mülltrennung** – TODO: Restmüll, Plastik, Papier.\n"
        "📅 Abholungstage: TODO"
    ),

    # 🌐 Kommunikation & Versorgung
    "wlan": (
        "📶 **WLAN**\n"
        "- Name (SSID): TODO-SSID\n"
        "- Passwort: TODO-PASS\n"
        "Tipp: Router ggf. neu starten bei Problemen."
    ),
    "wifi": "Alias von *wlan*.",
    "strom": "⚡ **Strom** – Sicherungskasten/FI-Schalter: TODO.",
    "wasser": "🚰 **Wasser** – Hauptabsperrhahn: TODO.",
    "gas": "🔥 **Gas** – Info zu Herd/Heizung: TODO.",

    # 🚑 Gesundheit & Notfall
    "notfall": (
        "🚨 **Notfallnummern**\n"
        "- Europaweiter Notruf: 112\n"
        "- Polizei: 113 (IT)\n"
        "- Ambulanza: 118\n"
        "- Feuerwehr: 115\n"
        "Adresse parat halten!"
    ),
    "arzt": "👩‍⚕️ **Nächster Arzt:** TODO Name, Adresse, Telefon.",
    "apotheke": "💊 **Apotheke:** TODO Name, Adresse, Öffnungszeiten.",
    "krankenhaus": "🏥 **Krankenhaus:** TODO Name, Adresse, Notaufnahme.",

    # 🍴 Versorgung & Tipps
    "einkaufen": (
        "🛒 **Einkaufen – kurz & knackig**\n"
        "- **S. Martino in Freddana:** Carrefour & Bäckerei.\n"
        "- Hauptstraße: „Alimentari Pini“ (Brot, Milch, Obst/Gemüse).\n"
    ),
    "einkauf": "Alias von *einkaufen*.",
    "supermarkt": "🛍️ **Supermarkt:** TODO Öffnungszeiten.",
    "bäckerei": "🥖 **Bäckerei:** TODO Öffnungszeiten.",
    "pizzeria": "🍕 **Pizzeria:** TODO Restaurantempfehlung.",
    "märkte": "🧺 **Wochenmärkte:** TODO Orte & Zeiten.",

    # 🚗 Mobilität
    "parken": "🅿️ **Parken:** TODO Stellplätze/Hinweise.",
    "tankstelle": "⛽ **Tankstelle:** TODO Nächste Tankstelle mit Adresse.",
    "bus": "🚌 **Bus:** TODO nächste Haltestelle & Linie.",

    # 🌳 Umgebung & Ausflüge
    "strand": "🏖️ **Nächster Strand:** TODO Name, Entfernung.",
    "sehenswürdigkeiten": "🏛️ **Sehenswürdigkeiten:** TODO Top-3-Tipps.",
    "wandern": "🥾 **Wandern:** TODO Startpunkte & Routen.",

    # 🍕 Pizzaofen (Haus-spezifisch)
    "pizza": "🍕 Pizza-Info folgt vor Ort – frag gern nach dem Pizzaofen-Setup.",

    # ℹ️ Hilfe
    "hilfe": "ℹ️ **Borgo-Bot** – Sende `!bot <Thema>`. Beispiele: `!bot wlan`, `!bot notfall`, `!bot einkaufen`."
}

FIXED_ALIASES: dict[str, str] = {
    "wifi": "wlan",
    "einkauf": "einkaufen",
    "?": "hilfe",
}

def fixed_help_text() -> str:
    """Hilfe baut sich dynamisch aus FIXED_RESPONSES auf."""
    keys = sorted(set(list(FIXED_RESPONSES.keys()) + list(FIXED_ALIASES.keys())))
    primaries = [k for k in keys if FIXED_ALIASES.get(k, k) == k]
    cmds = ", ".join(f"`{k}`" for k in primaries)
    return (
        "ℹ️ **Borgo-Bot Befehle (fix):** "
        + cmds +
        ".\nFrag sonst frei mit `!bot <Frage>` – ich nutze dann den Kontext (`borgobatone.txt`)."
    )

def try_fixed_response(cmd: str) -> str | None:
    """Liefert eine feste Antwort, falls cmd bekannt ist (inkl. Alias-Auflösung)."""
    key = FIXED_ALIASES.get(cmd, cmd)
    if key in FIXED_RESPONSES:
        return FIXED_RESPONSES[key]
    return None

def build_answer(cmd: str, rest: str) -> str:
    # 0) Aliasse normalisieren
    if cmd in FIXED_ALIASES:
        cmd = FIXED_ALIASES[cmd]

    # 1) Harte, sofortige Antworten (ohne LLM)
    fixed = try_fixed_response(cmd)
    if fixed is not None:
        return fixed

    # 2) Hilfe / unbekannt → kurzes, dynamisches Fallback
    if cmd in ("help", "hilfe", "", "?"):
        return fixed_help_text()

    # 3) Freier Prompt → LLM (mit Hot-Reload-Kontext)
    question = normalize_text(f"{cmd} {rest}".strip())
    if not question:
        return ("ℹ️ **Unklare Eingabe.** Beispiele: `!bot hallo`, `!bot einkaufen`, "
                "`!bot wo kann ich Brot kaufen?`")
    return llm_answer(question, load_context(False))
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