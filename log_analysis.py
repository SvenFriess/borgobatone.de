from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import logging
from datetime import datetime
import time
import uuid
import traceback
import json

# 🔧 Flask Setup
app = Flask(__name__)
CORS(app)

# 📄 Logging aktivieren
log_file_path = "/Users/svenfriess/Desktop/borgobatone.de/chatbot.log"
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)

# 📥 Kontext laden (nur 1x beim Start)
with open("/Users/svenfriess/Desktop/borgobatone.de/static/borgobatone.txt", "r", encoding="utf-8") as f:
    borgobatone_context = f.read()

# 🌐 Startseite mit Chat-Button
@app.route("/")
@app.route("/chat")
def chat_popup():
    ip_address = request.remote_addr
    user_agent = request.headers.get("User-Agent", "Unbekannt")
    logging.info(f"🌐 Aufruf von / durch {ip_address} mit User-Agent: {user_agent}")
    return render_template("chat.html")

# 📺 Nur Chatfenster
@app.route("/chatwindow")
def chat_window_only():
    ip_address = request.remote_addr
    user_agent = request.headers.get("User-Agent", "Unbekannt")
    logging.info(f"📺 Aufruf von /chatwindow durch {ip_address} mit User-Agent: {user_agent}")
    return render_template("chat_only.html")

# 🔍 Logge alle Antworten mit Statuscode, Pfad, IP und User-Agent
@app.after_request
def log_response(response):
    user_agent = request.headers.get("User-Agent", "Unbekannt")
    logging.info(f"🔍 {request.method} {request.path} → {response.status_code} von {request.remote_addr} mit User-Agent: {user_agent}")
    return response

# 🤖 API-Endpoint mit Kontext
@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()
    user_input = data.get("user_input", "")
    ip_address = request.remote_addr
    user_agent = request.headers.get("User-Agent", "Unbekannt")
    request_id = uuid.uuid4()

    logging.info(f"🟡 [{request_id}] Eingabe von {ip_address} mit User-Agent: {user_agent} – {user_input}")

    try:
        start_time = time.time()
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "llama3.1",
                "messages": [
                    {
                        "role": "system",
                        "content": "Du bist ein hilfsbereiter Chatbot für das Projekt Borgo Batone. Verwende den folgenden Kontext, um Fragen zu beantworten:\n\n" +
                                   borgobatone_context +
                                   "\n\nAntworte auf Deutsch in 2–3 Sätzen. Sei freundlich, klar und informativ."
                    },
                    {"role": "user", "content": user_input}
                ],
                "stream": False
            }
        )
        duration = round(time.time() - start_time, 2)
        response.raise_for_status()
        result = response.json()
        reply = result["message"]["content"]

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": str(request_id),
            "ip": ip_address,
            "user_agent": user_agent,
            "user_input": user_input,
            "response_time": duration,
            "reply": reply
        }
        logging.info("🟢 Antwort generiert: " + json.dumps(log_entry, ensure_ascii=False))

        return jsonify({"response": reply})
    except Exception as e:
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": str(request_id),
            "ip": ip_address,
            "user_agent": user_agent,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        logging.error("🔴 Fehler bei Anfrage: " + json.dumps(error_entry, ensure_ascii=False))
        return jsonify({"error": str(e)}), 500

# 🟢 Server starten
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5200)

