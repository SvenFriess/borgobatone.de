from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import logging
import time
import uuid
import traceback
import user_agents
import os
import difflib
import re

app = Flask(__name__)
CORS(app)

# Logging einrichten
log_file_path = os.path.join(os.getcwd(), "chatbot.log")
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)

# Kontextdatei laden
kontext_dateipfad = os.path.join("static", "borgobatone.txt")
with open(kontext_dateipfad, "r", encoding="utf-8") as f:
    borgobatone_context = f.read()

@app.route("/")
@app.route("/chat")
def chat_popup():
    return render_template("chat.html")

@app.route("/chatwindow")
def chat_window_only():
    return render_template("chat_only.html")

@app.after_request
def log_response(response):
    return response

@app.route("/api/generate", methods=["POST"])
def generate():
    request_id = uuid.uuid4()
    try:
        data = request.get_json()
        user_input = data.get("user_input", "").strip().lower()

        ip_address = request.remote_addr
        user_agent_str = request.headers.get("User-Agent", "Unbekannt")
        user_agent = user_agents.parse(user_agent_str)
        logging.info(f"🟡 [{request_id}] Eingabe von {ip_address} mit {user_agent.browser.family} auf {user_agent.os.family} – {user_input}")

        start_time = time.time()
        antwort = "Ich habe darauf leider keine passende Antwort gefunden."

        fragen_antworten = []
        for abschnitt in borgobatone_context.split("Frage: "):
            teile = abschnitt.split("Antwort:")
            if len(teile) == 2:
                frage, antw = teile
                fragen_antworten.append((frage.strip(), antw.strip()))

        fragen = [f[0].lower() for f in fragen_antworten]
        passende = difflib.get_close_matches(user_input, fragen, n=1, cutoff=0.5)

        if passende:
            index = fragen.index(passende[0])
            antwort = fragen_antworten[index][1]
            antwort = re.sub(r'\[a-z0-9]+', '', antwort).strip()

        dauer = round(time.time() - start_time, 2)
        logging.info(f"🟢 [{request_id}] Antwortdauer: {dauer} Sek. – {antwort}")
        return jsonify({"response": antwort})

    except Exception as e:
        logging.error(f"🔴 [{request_id}] Fehler: {str(e)}")
        traceback.print_exc()
        return jsonify({"response": "Interner Fehler beim Verarbeiten der Anfrage."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5200)