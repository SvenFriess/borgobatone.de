import subprocess
import time
import re
import logging
from local_llm_interface import ask_local_model

# 📞 Signal-CLI-Konfiguration
signal_cli_path = "/usr/local/bin/signal-cli"
phone_number = "+4915755901211"
group_id = "21oiqcpO37/ScyKFhmctf/45MQ5QYdN2h/VQp9WMKCM="  # Nur diese Gruppe beantworten
logger.info(f"[DEBUG] Eingegangen: group_id={group_id}, text={text!r}")

# 📁 Logging-Konfiguration
logfile = "logs/borgo_chatbot.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(logfile),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 🧠 Trigger & Antworten (Teiltreffer, alles lowercase)
TRIGGER_TERMS = {
    "hallo": "👋 Willkommen in Borgo Batone! Wie kann ich helfen?",
    "einkaufen": "🛒 **S. Martino in Freddana:** Carrefour & Bäckerei. Unten an der Hauptstraße: „Alimentari Pini“ (Brot, Milch, Obst/Gemüse).",
    "notfall": "🚨 **Notfall:** EU-Notruf **112**. Nächste Arztpraxis: Hauptstraße 5, Tel.: 01234-56789.",
    "pizzaofen": "🍕 **Pizzaofen – Kurz:** 1) Holz klein anfeuern, 2) 20–30 min vorheizen, 3) Glut zur Seite, 4) Stein wischen, 5) Pizza ~90 s backen.",
    "müll": "♻️ **Mülltrennung:** Rest (grau), Papier (blau), Plastik/Metall (gelb), Glas (Container im Ort).",
    "wlan": "📶 **WLAN:** SSID: *Borgo-Guest* • Passwort: *<HIER_EINTRAGEN>*",
    "hund": "🐕 **Hunde:** Leine im Dorf, keine Hunde am Pool, Hinterlassenschaften entsorgen.",
    "pool": "🏊 **Pool:** 9–20 Uhr, vorher duschen, keine Glasflaschen, Kinder nur mit Begleitung.",
    "gemeinschaftsküche": "🍽️ **Gemeinschaftsküche:** Sauber hinterlassen, Fächer beschriften, Spülmaschine abends starten.",
    "waschmaschine": "🧺 **Waschmaschine:** Nebenraum bei der Küche; Nutzung 8–20 Uhr; Tabs im Schrank oben.",
    "fahrrad": "🚲 **Fahrräder:** Schuppen am unteren Parkplatz. Schloss-Code: *<CODE_EINTRAGEN>*. Bitte wieder anschließen.",
    "alarmanlage": "🔐 **Alarmanlage:** Code: *<CODE_EINTRAGEN>* – bei Verlassen aktivieren/deaktivieren.",
    "wasser": "💧 **Trinkwasser:** Quelle am unteren Weg, links Richtung Hauptstraße („Acqua potabile“).",
    "wie ist das wetter?": "🌤️ **Demo:** Wetterabfrage liefert hier eine Standardantwort.",
    # Ergänzende allgemeine Begriffe
    "öffnungszeiten": "🕒 **Öffnungszeiten:** Kleine Läden oft 12–16 Uhr geschlossen (Siesta).",
    "arzt": "🏥 **Arzt:** Hausarzt S. Martino; Notdienst (Italien) laut Aushang – lokal prüfen.",
    "transport": "🚗 **Transport:** Nächster Bahnhof: Lucca; Busse unregelmäßig – Auto empfohlen.",
    "karte": "🗺️ **Karte:** Lucca 20–30 min, Küste 30–40 min. Details in der Infomappe.",
    "veranstaltungen": "🎉 **Veranstaltungen:** Aushang im Gemeinschaftsraum oder in der Signal-Gruppe nachfragen.",
    "hilfe": "🆘 **Hilfe:** Frag mich zu Notfall, WLAN, Küche, Pool, Pizzaofen, u. v. m.",
    "wetter": "⛅ **Wetter (allg.):** Sommer heiß/trocken, Abende teils frisch. Für Live-Wetter bitte App."
}

FALLBACK_ANSWER = "ℹ️ **Unbekanntes Anliegen.** Beispiele: `!Bot hallo`, `!Bot einkaufen`, `!Bot notfall`, `!Bot wlan`, `!Bot pool`, `!Bot pizzaofen`."

def finde_triggerantwort(nachricht: str) -> str:
    """
    Prüft, ob die Nachricht einen der Trigger enthält (teilweise Übereinstimmung).
    Rückgabe: feste Antwort oder leerer String, wenn kein Treffer.
    """
    inhalt = nachricht.lower().replace("!bot", "").strip()
    # Längere Keys zuerst testen (damit 'wie ist das wetter?' vor 'wetter' greift)
    for key in sorted(TRIGGER_TERMS.keys(), key=len, reverse=True):
        if key in inhalt:
            return TRIGGER_TERMS[key]
    return ""

def sende_antwort(text: str):
    try:
        subprocess.run([
            signal_cli_path, "-u", phone_number, "send",
            "-g", group_id, "-m", text
        ], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Fehler beim Senden: {e}")

def main_loop():
    while True:
        try:
            logger.info("📡 Starte Empfang (signal-cli receive) – Gruppe fix: %s", group_id)
            process = subprocess.Popen(
                [signal_cli_path, "-u", phone_number, "receive"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            current_group = ""
            for raw in process.stdout:
                line = raw.strip()
                if not line:
                    continue

                # Gruppe (best effort: verschiedene Varianten abfangen)
                mg = re.search(r"(Group(?: ID)?):\s*([A-Za-z0-9+/=]+)", line, flags=re.IGNORECASE)
                if mg:
                    current_group = mg.group(2)
                    continue

                # Nachricht
                mm = re.search(r"Body:\s*(.*)", line)
                if mm:
                    nachricht = mm.group(1).strip()
                    logger.info(f"📩 Nachricht: {nachricht}  | Gruppe: {current_group or '-'}")

                    # Nur antworten, wenn die erlaubte Gruppe erkannt wurde (falls erkennbar)
                    if current_group and current_group != group_id:
                        logger.debug("➡️ Andere Gruppe (%s) – ignoriere.", current_group)
                        continue

                    if nachricht.lower().startswith("!bot"):
                        antwort_fest = finde_triggerantwort(nachricht)
                        if antwort_fest:
                            logger.info("⚡ Fester Trigger → direkte Antwort")
                            sende_antwort(antwort_fest)
                        else:
                            logger.info("💬 Kein Trigger → leite an LLM weiter")
                            try:
                                antwort = ask_local_model(nachricht)
                            except Exception as e:
                                logger.exception("LLM-Fehler, sende Fallback.")
                                antwort = FALLBACK_ANSWER
                            sende_antwort(antwort)
                    else:
                        logger.debug("🔕 Keine Bot-Nachricht – ignoriere.")
        except Exception as e:
            logger.warning("⚠️ Receive beendet/Fehler: %s – Neustart in 5 s …", e)
            time.sleep(5)

if __name__ == "__main__":
    main_loop()